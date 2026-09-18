# Math Category Primer Pipeline

For the Hermes research sweep, each of the 44 math/theory categories needs a field primer:
a dense, Hermes-focused summary of what the field is, key results, standard tools,
and specifically how it maps to Hermes components (context compression, skill routing,
memory pipeline, model routing, etc.).

## Files

  ~/.hermes/scripts/math-primers-overnight.py  — batch primer generator
  ~/.hermes/scripts/math-paper-interpreter.py  — paper classification using primers
  ~/.hermes/cache/research/primers/<cat>.txt   — generated primers (50 total)
  ~/.hermes/skills/research/hermes-research/references/primer-<cat>.txt  — skill refs

## Primer Format (what to instruct the LLM to produce)

Each primer should start with `PRIMER: <Field Name>` on line 1, then cover:
1. Core concepts and notation (dense, not introductory)
2. Key results the field is known for (theorems, bounds, impossibility results)
3. Standard practitioner tools
4. Hermes Applications section: for each major concept, (a) what Hermes component
   has analogous structure, (b) what current heuristic does, (c) what a principled
   approach would do differently, (d) honest value assessment (worth it / overkill)
5. Spike Candidates: 2-3 concrete Given/When/Then experiment candidates
6. Optimizations: 1-2 concrete formula/bound replacements for existing heuristics

## Interpretation Flow (paper -> spike or optimization)

1. Sweep finds paper in math category
2. math-paper-interpreter.py loads primer for that category (~2000 char prefix)
3. Interpreter checks paper abstract against primer's Hermes Applications section
   (not just generic keyword matching)
4. Classification: OPTIMIZATION (replace heuristic with formula) | SPIKE (new structure
   to explore) | SKIP (no Hermes analogue after honest assessment)
5. Confidence boosted to 'high' when paper content matches primer's spike candidates
   or hermes applications section; stays 'medium'/'low' without primer or on mismatch
6. SKIP still fires for pure math papers even when primer is present

## Category Priority (when primers need to be regenerated or reviewed)

Tier 1 (score 20-25, most direct Hermes relevance):
  information_theory, online_learning, generalization_theory, game_theory,
  stochastic_causal, multiagent_systems_theory, rl_theory_comprehensive

Tier 2 (score 16-20):
  convex_analysis, spectral_graph_theory, formal_language_automata, robust_stats,
  numerical_optimization, monte_carlo_methods

Tier 3 (score 6-12, useful but abstract):
  algebraic_topology, category_theory, information_geometry, dynamical_systems,
  mean_field_large_dev, random_graphs
