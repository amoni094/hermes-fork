# Skill Architecture Research — Post-Aug 8 2026 Sweep

Research sweep completed Aug 11, 2026. Net-new findings relative to Aug 8 baseline.
Baseline (already in skills): Open Agent Passport YAML policy, GoS dependency graph,
SSL risk_level frontmatter, VoltAgent semantic skill catalog, YAML+markdown format.

---

## 1. SkillReact — Compositional Risk Detection at Install Time
**Source:** arXiv:2606.00448v1, May 30, 2026 (multiple Chinese + US authors)
**Dataset:** 1,520 ClawHub skills; 211,575 individually-safe pairs evaluated
**Key result:** 18.2% of flagged skill *pairs* contain genuine compositional risk (population-weighted validity). Per-skill scanning misses all of these by construction — every pair is individually safe.

**The core problem:** two individually-safe skills can create an unsafe *installed set* through capability union.
Example: Skill A = file-read only. Skill B = network-out only. Both pass per-skill review.
Together: {file_read ∧ network_out} = data exfiltration capability.

**10 forbidden capability patterns (from paper):**
Primary: `{file_read ∧ network_out}`, `{credential_access ∧ network_out}`,
`{shell_exec ∧ network_out}`, `{file_write ∧ shell_exec}`, etc.
Full list not published — use these as minimum set.

**SkillReact 3-component framework:**
1. Deterministic static-composition benchmark (capability union check against forbidden patterns)
2. LLM-assisted human-adjudication pipeline (calibrates static flags → ~1 in 5 is a real risk)
3. Action-based exploitability harness (tests when model actually issues tool calls)

**Key empirical finding on model disposition:**
- Haiku-4-5: issues full download-then-execute chain on 36/39 direct-prompt trials
- Sonnet-4-6: refuses outright
- Opus-4-7: stops at download stage
- **Compliance is HIGHEST with NO skills installed** — composition fixes which capabilities are reachable; the host model decides whether to use them

**Hermes SKILL.md implementation:**
```yaml
# Add to SKILL.md frontmatter:
capabilities:
  - file_read          # can read files from disk
  - network_out        # can make outbound HTTP calls
  - shell_exec         # can execute shell commands
  - credential_access  # can read API keys or secrets
  - file_write         # can write files
```

**Install-time check (Python pseudocode):**
```python
FORBIDDEN_PAIRS = [
    {"file_read", "network_out"},      # exfiltration
    {"credential_access", "network_out"},  # credential theft
    {"shell_exec", "network_out"},     # C2 channel
    {"file_write", "shell_exec"},      # persistence
]

def check_compositional_risk(installed_skills: list[dict]) -> list[str]:
    cap_union = set()
    for skill in installed_skills:
        cap_union |= set(skill.get("capabilities", []))
    violations = []
    for pattern in FORBIDDEN_PAIRS:
        if pattern.issubset(cap_union):
            violations.append(str(pattern))
    return violations
```

**No code released** — methodology fully specified in paper.

---

## 2. Agent Skill Evaluation & Evolution — 4-Paradigm Taxonomy
**Source:** arXiv:2606.11435v1, Rutgers University, June 9, 2026
**GitHub:** https://github.com/Cassie07/AgentSkill_Survey  ← code available

**Formal skill definition:** `S = (C, π, T, R)` where:
- `C: O × G → {0,1}` — condition mapping observation + goal to skill relevance
- `π` — execution policy (procedural steps)
- `T` — termination criterion (when skill is complete)
- `R` — reusable interface for composition with other skills

**4 evolution paradigms:**

| Paradigm | Signal | Strength | Pitfall |
|---|---|---|---|
| Execution feedback | Runtime failure/success | High-fidelity failure correction | Signal sparse when environment is narrow/deterministic |
| Trajectory distillation | Multi-run patterns | Captures reusable knowledge | Requires curated high-quality trajectories; don't use all traces indiscriminately |
| Compression/augmentation | Token efficiency | Reduces load | Can remove task-critical procedural steps |
| RL with reusable rewards | Group task reuse | Generalizable skills | Agent may learn to bypass skill library entirely |

**Critical pitfall — compression:**
Before compressing skill content for token efficiency, annotate core executable steps as `protected` (cannot be removed). After compression, run the evolved skill against a held-out task set to confirm performance is preserved.

**Hermes SKILL.md application:**
```yaml
# Add to SKILL.md frontmatter:
protected_steps:
  - "Step 3: Run verification command"
  - "Step 7: Check exit code before proceeding"
```

**Dual-rollout evaluation protocol (detect reward hacking):**
At regular intervals, evaluate task performance BOTH with and without skills.
Treat the performance GAP as the skill contribution signal.
A **shrinking gap** over training iterations = agent learning to bypass skill library.
Trigger: review reward design when gap shrinks below threshold.

**Implementation for Hermes:**
```python
# Weekly skill contribution audit
for skill in active_skills:
    tasks = sample_tasks_from_triggers(skill, n=3)
    score_with = evaluate_tasks(tasks, skill_loaded=True)
    score_without = evaluate_tasks(tasks, skill_loaded=False)
    contribution = score_with - score_without
    log_to_sqlite("skill_contributions", {
        "skill": skill.name,
        "date": today,
        "contribution_delta": contribution
    })
    if contribution < 0:
        flag_for_review(skill)
```

**Six benchmark categories identified (coverage gaps):**
1. General-domain (WebArena, OSWorld) — most coverage
2. Code/software dev (SWE-bench) — good coverage
3. Multimodal (GUI) — sparse
4. Embodied (Minecraft/MineDojo) — good for composition
5. Memory + conversation — improving
6. **Skill security** — almost no coverage (SkillReact is the exception)

---

## 3. SkillComposer — Small Composer LM + Large Executor LM
**Source:** arXiv:2606.06079v1 (referenced in survey), June 2026
**Result:** 4B SkillComposer improves 27B executor by +4.5pp on agent tasks, +3.4pp on code tasks; generalizes across domains.

**Core insight:** skill composition (WHEN and HOW to combine skills) is a **separable** concern from skill execution. A small specialized model can be trained just for composition decisions.

**Architecture:**
- Small model (4B) = "SkillComposer" — decides which skills to activate and in what order
- Large model (27B) = "Executor" — actually runs the skill actions
- Composition decisions are made by the small model without querying the large model

**Hermes application:** Rather than using the main agent model for skill routing, consider a dedicated lightweight classifier (even a fine-tuned small model or rules-based classifier) trained on `(task_description, available_skills) → skill_selection`. Decouples routing from reasoning.

---

## 4. CoevoSkills — Self-Evolving Skills via Co-Evolutionary Verification
**Source:** Referenced in arXiv:2606.11435v1 as arXiv:2606.nnnnn (exact ID not captured)
**Referenced in:** AgentSkill Survey (Rutgers, 2026)

**Pattern:** Co-evolutionary verification where skill evolution and evaluation co-evolve — the evaluator for a skill is updated alongside the skill itself. Prevents the evaluator from becoming stale as the skill evolves.

**Hermes application:** When updating a SKILL.md, also update the `triggers` block (which functions as the relevance evaluator). Skills that evolve without updating triggers become invisible to the routing system.

---

## 5. Self-Evolving Ontologies for Agent Knowledge Graphs
**Source:** Medium/Graph Praxis: "How Self-Evolving Ontologies Close the Loop" (2026);
Evontree arXiv:2510.26683

**Key insight:** Zero-shot relation extraction (framing predicate identification as reading comprehension) enables agents to name — and therefore retain — new relationship types discovered at runtime, closing the ontology growth loop without manual schema updates.

**Evontree result:** Ontology rule-guided self-evolution works in low-resource specialized domains. LLMs guided by ontology rules generate better skills than unconstrained generation.

**The "can't name it, can't learn it" failure mode:** if an agent observes a new relationship type but the ontology has no predicate for it, the fact gets stored as unstructured text (poor retrieval) or dropped entirely.

**Hermes implementation:**
When Hindsight extracts a fact that doesn't match existing Graphiti node types, run a zero-shot haiku call:
```
"What type of relationship is: [subject] → [object]?
Return: {predicate: str, confidence: float}"
```
If confidence ≥ 0.75, register the new predicate as a Graphiti node-type before committing.
Log new predicates to `ontology_extensions` table in SQLite for curator review.

---

## 6. Auton AgenticFormat — Config Schema Best Practices (Snapchat AI)
**Source:** arXiv:2602.23720v1, Feb 27, 2026

**AgenticFormat standard (YAML/JSON):**
```yaml
agent:
  id: "unique-agent-id"
  version: "1.0.0"
  identity:
    role: "..."
    objective: "..."
  capabilities:
    tools: [...]
    memory:
      type: "hierarchical"
      consolidation: "reflector-driven"
  constraints:
    manifold:
      - deny: ["file_read AND network_out"]
      - require_approval: ["credential_access"]
  evolution:
    level: "in_context"  # in_context | fine_tuning | rl
```

**4 architectural pillars:**
1. **Cognitive Blueprint** — declarative spec (the YAML/JSON) — versionable, auditable data artifact
2. **Runtime Engine** — platform-specific execution (loads + runs the blueprint)
3. **Constraint Manifold** — safe action subspace enforcement before emission
4. **Cognitive Map-Reduce** — parallel execution bounded by critical path

**Industry convergence (2026):** CrewAI, LangGraph 2.x, AutoGen 0.5 all converge on:
- YAML-first agent definitions (declarative > in-code)
- Explicit role/goal/tool separation
- First-class `termination_condition` in config
- Team-level configuration for multi-agent orchestration

**Hermes SKILL.md gap:** Missing `team_config` blocks for multi-skill orchestration and explicit `termination_condition` fields mirroring LangGraph's checkpointing pattern.

---

## Pitfalls (from this sweep)

- **Per-skill scanning is insufficient:** SkillReact proves that passing individual skill review gives false safety confidence for skill ecosystems. Always check pairwise capability union at install time.
- **Compositional risk is model-disposition gated:** a compositional risk doesn't automatically realize as an exploit — the host model's refusal behavior is the second gate. Measure both static candidates AND model-conditional realization separately.
- **Compression before protection = information loss:** annotate `protected_steps` before any compression/augmentation pass.
- **Ontology growth loop:** an agent that can observe but not name new relationship types will systematically lose that knowledge. Implement zero-shot predicate registration.
- **Dual-rollout is the only honest skill contribution metric:** task success rate WITH skills is not the right metric — an agent can achieve the same score by routing around skills entirely. The delta is what matters.
