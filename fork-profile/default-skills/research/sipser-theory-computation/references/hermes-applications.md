# Sipser — Hermes Agent Applications

## Overview

Theory of computation gives Hermes formal grounding for four agent-relevant problems:

1. **Halting detection** — agent loop termination
2. **Complexity-gated planning** — task routing by computational tractability
3. **Pumping lemma as anti-pattern detector** — skill routing pattern analysis
4. **Regex optimization** — efficient skill trigger matching

---

## 1. Halting Detection for Agent Loops

### Theoretical foundation

**Theorem 4.11 (Sipser):** ATM is undecidable. No algorithm correctly decides for all ⟨M,w⟩ whether M halts on w.

By reduction, detecting whether a Hermes agent loop terminates is undecidable in general: an agent is a TM, its task is an input, and "does this agent ever return?" is equivalent to ATM.

### Hermes heuristic (correct framing)

Since the halting problem is undecidable, Hermes cannot *detect* loop termination — it can only *bound* it:

```python
# Pattern: bounded loop with divergence detection
MAX_STEPS = agent_config.max_steps  # e.g., 50
last_state_hashes = deque(maxlen=10)

for step in range(MAX_STEPS):
    action = agent.step(observation)
    state_hash = hash_state(observation, action)
    
    if state_hash in last_state_hashes:
        # Cycle detected — probable non-termination
        trigger_recovery()
        break
    last_state_hashes.append(state_hash)
    
    observation = env.apply(action)
    if agent.is_done(observation):
        break
else:
    # Exhausted steps — probable divergence
    trigger_recovery()
```

**Key points:**
- Cycle detection (repeating ⟨state, action⟩ pairs) is a *necessary* but not *sufficient* condition for looping — a loop can avoid simple state repeats
- Timeout is the primary safety net; cycle detection is a fast early exit
- Document the heuristic as a heuristic — do not claim it detects all loops

### When to apply

- `agent-runtime-loop-patterns` encounters infinite retry
- Tool call rate drops to zero but agent does not complete
- Memory usage grows unboundedly across steps

---

## 2. Complexity-Gated Planning

### Theoretical foundation (Ch 7–9)

Problems fall into complexity classes that predict tractability:

| Class | Characterization | Agent implication |
|-------|-----------------|-------------------|
| P | Polynomial-time decidable | Solve directly; fast |
| NP | Polynomial verifiable | Heuristics / approximation / timeout |
| PSPACE | Polynomial space (exponential time likely) | State-space search; bound depth |
| EXPTIME | Exponential time | Infeasible beyond small inputs |
| Undecidable | No algorithm | Impossible in general; bound heuristically |

### Gate logic for task planning

```python
def classify_task_complexity(task: str) -> str:
    """
    Returns: 'P', 'NP', 'PSPACE', 'UNDECIDABLE'
    Based on Sipser Ch 7-9 complexity class indicators.
    """
    NP_INDICATORS = [
        "schedule", "assign", "optimize", "satisfy constraints",
        "cover", "pack", "partition", "route all", "find minimum set"
    ]
    PSPACE_INDICATORS = [
        "plan in adversarial environment", "game strategy",
        "verify all paths", "full state space search"
    ]
    UNDECIDABLE_INDICATORS = [
        "determine if this program terminates",
        "verify semantic equivalence of two programs",
        "check all possible inputs"
    ]
    
    task_lower = task.lower()
    if any(kw in task_lower for kw in UNDECIDABLE_INDICATORS):
        return "UNDECIDABLE"
    if any(kw in task_lower for kw in PSPACE_INDICATORS):
        return "PSPACE"
    if any(kw in task_lower for kw in NP_INDICATORS):
        return "NP"
    return "P"

def plan_with_complexity_gate(task: str):
    complexity = classify_task_complexity(task)
    if complexity == "P":
        return direct_solve(task)
    elif complexity == "NP":
        return approximate_or_bound(task, timeout=30)
    elif complexity == "PSPACE":
        return heuristic_search(task, max_depth=5)
    elif complexity == "UNDECIDABLE":
        return heuristic_bound(task)
```

### Practical decision tree

```
Is the task a decision problem over a well-defined finite structure?
├── Yes: Does a known polynomial algorithm exist? (check CLRS)
│   ├── Yes → P: use it directly
│   └── No: Is the task NP-complete (reduce from 3SAT/CLIQUE)?
│       ├── Yes → NP: use approximation or branch-and-bound with timeout
│       └── Unknown → assume NP; apply heuristic
└── No: Does the task involve checking ALL configurations?
    ├── Yes → PSPACE: bound depth/breadth
    └── No: Is it about TM behavior? → Likely undecidable; use heuristic
```

---

## 3. Pumping Lemma as Anti-Pattern Detector

### Theoretical foundation (Ch 1.4, 2.3)

**Pumping Lemma (regular):** Regular languages are closed under repetition — any long-enough string can be "pumped" (the y segment repeated k times) and remain in the language.

**Implication:** If a proposed pattern for skill routing *cannot* be pumped while remaining valid, the pattern is **not regular** — no DFA/regex can express it.

### Diagnostic questions

For a proposed skill routing pattern P:

1. **Can it be expressed by counting?** (e.g., "exactly n keywords") → Not regular (counting to arbitrary n requires memory)
2. **Does it require balanced matching?** (e.g., "open parens match close parens") → Not regular, likely context-free
3. **Does it require two separate counting constraints?** (e.g., "n keywords AND n values") → Not context-free (CFL pumping lemma)

### Classification and remedy

| Pattern type | Class | Hermes remedy |
|-------------|-------|---------------|
| Fixed string, bounded wildcards | Regular | Regex, DFA |
| Balanced structure (JSON, XML) | CFL | Parser (recursive descent, PDA) |
| Two simultaneous counting constraints | Beyond CFL | Custom validator, semantic check |
| Semantic meaning | Undecidable (in general) | Embedding similarity |

### Example application

**Bad:** Regex `(tool_call\s+\w+\s+)+` to count balanced tool call/result pairs — not regular, will false-match on unbalanced sequences.

**Good:** Write a stack-based parser that counts nesting depth; it is a PDA computation and correctly handles the context-free structure.

---

## 4. Regular Expression Optimization for Skill Routing

### Theoretical foundation (Ch 1.3)

Skill routing at Hermes often uses pattern matching on trigger strings. Regex engines may backtrack exponentially on ambiguous patterns. DFA-based matching is always O(n) in input length.

### Optimization rules

1. **Compile to DFA at load time** (not per-query): Use Python's `re.compile()` once; or convert to explicit DFA using automaton library.

2. **Avoid catastrophic backtracking patterns:**
   ```
   BAD:  (a+)+           # exponential on "aaa...b"
   BAD:  (a|aa)+         # exponential overlap
   GOOD: a+              # deterministic
   ```

3. **Merge overlapping patterns via union:** If multiple skills share trigger prefixes, build a combined NFA → DFA (subset construction) to evaluate all at once.

4. **Use possessive quantifiers or atomic groups** where supported to prevent backtracking:
   ```python
   # Python regex possessive (regex library):
   import regex
   pattern = regex.compile(r'(?:skill_\w+)++')
   ```

5. **Detect non-regular skill triggers** via pumping lemma analysis (section 3 above); replace with parsers.

### Subset construction sketch (for multiple skill patterns)

```python
from collections import defaultdict

def build_combined_dfa(skill_patterns: dict[str, str]) -> callable:
    """
    Given {skill_name: regex_pattern}, build a single DFA
    that routes any input to the first matching skill in O(n).
    Uses Python's re module as a DFA approximation.
    """
    combined = '|'.join(f'(?P<{name}>{pat})' 
                        for name, pat in skill_patterns.items())
    compiled = re.compile(combined)
    
    def route(text: str) -> str | None:
        m = compiled.search(text)
        return m.lastgroup if m else None
    
    return route
```

---

## Cross-Skill Integration

| Sipser concept | Hermes skill to pair with |
|---------------|--------------------------|
| Halting heuristics | `agent-runtime-loop-patterns` |
| Complexity gating | `complexity-gated-planning`, `adaptive-agent-reasoning` |
| Pattern classification | `hermes-semantic-skill-routing` |
| Decidability of agent properties | `systematic-debugging` |
| Approximation algorithms | `gepa-omni-optimization` |
