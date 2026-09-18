## Research basis for recursive adversarial loop design

- **RCI — Recursive Criticize and Improve** (Kim et al., arXiv:2303.17491, NeurIPS 2023):
  LLM explicitly names flaws in its output, then regenerates. RCI + CoT beats either alone.
  Key mechanism: articulate "the flaw is X, the correct form is Z" before rewriting — don't
  skip from finding to edit. The explicit step-out reliably improves fix quality.

- **Reflexion — Verbal Reinforcement Learning** (Shinn et al., arXiv:2303.11366, NeurIPS 2023):
  Agents store reflective traces in episodic memory to avoid repeating the same error class
  in subsequent trials. The Reflexion agent achieved 91% HumanEval pass@1 (vs GPT-4's 80%
  baseline on the same benchmark) — this is a benchmark for the Reflexion coding agent, not
  for adversarial review per se. Core insight: making prior failure classes visible at inference
  time prevents re-introduction of fixed errors. Directly motivates the error-class carry-forward
  log in this skill's loop.

- **Self-RAG** (Asai et al., arXiv:2310.11511, ICLR 2024): reflection tokens inline with
  generation enable selective, on-demand critique. Suggests critique markers should be produced
  during review (not only in a post-hoc summary) to catch errors as they surface.

- **CoT step-length** (Jin et al., arXiv:2401.04925, ACL 2024 Findings): longer reasoning
  chains improve quality even without new information. Each reasoning step in the critique phase
  has compounding value — do not short-circuit the critique step to save tokens.

- **SkillOpt** (arXiv:2605.23904, Microsoft Research): bounded add/delete/replace edits to
  procedural memory docs, accepted only on quality improvement. Informs how this skill itself
  should be improved: always require a documented failure reason before patching.

- **skill_view(name='verification-before-completion')** — for the broader verification pattern
  (unit tests, linters, integration checks). Adversarial review sits alongside these checks,
  not replacing them.

- **PICon — Chained Interrogation for Agent Consistency** (arXiv:2603.25620, KAIST, 2026):
  Evaluates agent consistency through logically chained multi-turn questioning across three
  dimensions: internal (no self-contradiction), external (real-world fact alignment), and
  retest (stability under repetition). Even "highly consistent" systems fail the human baseline
  under chained questioning. Apply this to adversarial review of skill definitions and agent
  personas: question the skill's claims across multiple angles, not just in isolation.
  Chained interrogation pattern: State claim A → derive implication B from A → check if agent
  agrees with B → check if B contradicts any prior claim C. Single-turn adversarial review
  misses contradictions that only emerge across chains.

- **Salience Normalization** (arXiv:2607.17535, Chinese authors): Adversarial review of
  RAG-augmented outputs should check for salience-channel manipulation — conclusions that
  appear supported because they're positioned, repeated, or framed prominently in retrieved
  context, not because they have the most evidentiary support. A claim that appears first
  or most frequently in retrieved chunks is not necessarily the most well-supported one.
  Counter: reorder retrieved chunks by embedding score, not by source position, before review.
