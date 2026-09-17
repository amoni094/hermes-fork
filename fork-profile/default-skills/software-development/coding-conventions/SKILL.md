---
name: coding-conventions
category: software-development
description: Use when writing or reviewing code. Enforces code style.
---

# Coding Conventions

Researched and updated September 2026 (academic, web, GitHub, community sources).

Always check the local project first. If the repo has a formatter, linter, or
existing style, match it. Apply this skill when no house style exists, or when
creating new code in a mixed/no-style context.

**Override order (highest wins):**
1. Security and correctness
2. Repo formatter/linter/CI
3. Local consistency with adjacent files
4. This skill

**The meta-rule: format in CI, review for behavior.** Formatting debates are
settled by tooling. Spend review attention on bugs, security, architecture, and
LLM-specific defect patterns -- not whitespace.

---

## 1. Naming

**Intent over implementation.** Names are ~70% of source tokens and the primary
channel for both human comprehension and LLM reasoning. Misleading names are
first-class defects.

| Kind | Python | JS/TS | Go | Rust | Shell | SQL |
|---|---|---|---|---|---|---|
| Variables / functions | `snake_case` | `lowerCamelCase` | `camelCase` (unexported) / `PascalCase` (exported) | `snake_case` | `snake_case` | `snake_case` |
| Classes / types | `CapWords` | `PascalCase` | `PascalCase` | `PascalCase` | n/a | n/a |
| Constants | `UPPER_SNAKE` | `CONSTANT_CASE` (module-level) | `MixedCaps` (e.g. `MaxLength`) | `SCREAMING_SNAKE` | `UPPER_SNAKE` | n/a |
| Files / modules | `snake_case.py` | PascalCase if default export | `snake_case.go` | `snake_case.rs` | `foo.sh` | `snake_case` |
| Errors / exceptions | `FooError` | `FooError` class | `ErrFoo` var, `FooError` type | `FooError` | n/a | n/a |

**Do:**
- Descriptive domain compounds; length scales with scope (`i` OK in a 5-line loop)
- Booleans read as predicates: `is_ready`, `hasToken`, `canRetry`
- Python acronyms in CapWords: `HTTPServerError` (not `HttpServerError`)
- Trailing `_` to avoid keyword collision (`class_`, `type_`)
- Go: short names in small scope, longer names at package level

**Don't:**
- Single-letter `l`, `O`, `I` (look like 1/0)
- Type-encoded names (`id_to_name_dict`, `strName`, `arrItems`)
- Invent `__dunder__` names (Python)
- Interior-dropped abbreviations (`resMod` -> `response_model`)
- **Lookalike identifiers in the same module** -- `writer` for two distinct types
  confuses humans and LLMs equally (lint for homonyms; empirically documented)
- Review LLM-generated names as first-class defects: they are optimized for
  plausibility, not accuracy

```
# yes                         # no
user_count = 3                usrCnt = 3
class HttpClient              class http_client
MAX_RETRY_COUNT = 5           maxRetryCount = 5   # Python constant
function fetchUser(id)        function Fetch_User(id)  # JS
```

---

## 2. Formatting

**One formatter per language. Commit its config. Never hand-format against it.**
Formatting beyond indentation has mostly null results on comprehension in
controlled studies -- automate and stop debating.

| Language | Formatter | Linter |
|---|---|---|
| Python | `ruff format` (or Black) | `ruff check` (replaces flake8+isort+pyupgrade) |
| JS/TS | Biome (greenfield) or Prettier | Biome or Oxlint + ESLint |
| Go | `gofmt` / `goimports` | `go vet` + staticcheck |
| Rust | `rustfmt` | Clippy (`-D warnings` in CI) |
| Shell | `shfmt` | ShellCheck |
| SQL | `sqlfluff` | sqlfluff |
| Terraform | `terraform fmt -recursive` | tflint |
| Docker | n/a | hadolint |

**Key defaults:**
- Python: 79 cols per PEP 8; 88 cols is the Black/Ruff default -- follow repo config, default to 88 if none
- JS/TS: Biome defaults to **tabs**; Prettier defaults to **spaces**. Pick one;
  `biome migrate prettier` if switching
- Go: gofmt is non-negotiable; 80-col soft
- Rust: rustfmt defaults; 4 spaces

**`.editorconfig` at repo root** (lowest-common-denominator; formatters override):
```ini
root = true
[*]
indent_style = space
indent_size = 2
end_of_line = lf
charset = utf-8
trim_trailing_whitespace = true
insert_final_newline = true
[*.md]
trim_trailing_whitespace = false
[*.{py,rs,go}]
indent_size = 4
[Makefile]
indent_style = tab
[*.tf]
indent_size = 2
```

**SQL river alignment** (keywords right-aligned, identifiers left):
```sql
SELECT a.title,
       a.release_date
  FROM albums AS a
 WHERE a.title = 'Charcoal Lane';
```

---

## 3. Comments and documentation

**Comment why, not what.** Code that needs narration of what should be renamed
or extracted. Stale comments are actively harmful -- update or delete with the code.

**When to comment:**
- Non-obvious constraints, workarounds, invariants, performance traps
- SATD (self-admitted technical debt): `TODO(owner): action -- why` with type
  (`design`/`requirement`/`test`/`perf`/`docs`). Bare `TODO` without owner+reason is noise.
  Effort to repay by type (Li et al. PRESTI): docs debt < non-SATD < requirement debt --
  prioritize requirement/design/test debt over docs debt in repayment planning.
- Public API contracts
- Rust `unsafe`: must have `// SAFETY: ...` block explaining the invariant

**When not to:**
- Restate the next line (`i += 1  # increment i`)
- Commented-out code (use VCS)
- Auto-generated narrative (rots faster than hand-written; misleads LLMs)
- License boilerplate duplicated in every function

**Python docstrings (PEP 257 + Google style):**
- Triple double-quotes. One-line: `"""Return the hostname."""` on one line.
- Imperative mood: `Return the hostname.` not `Returns the hostname.`
- Google sections: `Args:`, `Returns:`, `Raises:`, `Yields:`
- Document every public module, class, method

```python
# yes
def connect(port: int) -> socket.socket:
    """Open a TCP socket to localhost.

    Raises:
        ConnectionError: no listener on port.
    """

# no
def connect(port):
    """This function connects to a port."""  # restates the name
```

**JSDoc/TS:** prefer TypeScript types over `@param {string}` duplication. Use
`@returns`, `@throws` only when they add info the signature doesn't.

**Hoare triples as the docstring contract (Huth & Ryan, Ch 4).** Every non-trivial
function has an implicit triple `{P} C {Q}`: precondition `P` (what must be true
on entry), command `C` (the body), postcondition `Q` (what is guaranteed on exit).
Types are not a substitute for `Q`. For any function with complex state, make `P`
and `Q` explicit in the docstring (`Args`/`Raises` cover part of `P`; `Returns`
must state `Q`, including what did *not* change when that matters). Use a logical
variable (`x0`) when the body mutates an input you still need to mention in `Q`.
Partial vs total: if the function may not return (loop, block, never-resolve),
`Q` is only a partial spec — say so.

**Loop invariants (Hoare while-rule; reinforces CLRS).** A loop is the triple
`{I} loop {I}`: `I` holds on entry, the body preserves `I` when the guard is true,
and `I ∧ ¬guard` must imply the loop's postcondition. Without `I`, loop correctness
cannot be verified. Non-obvious loops: write `I` next to the loop (comment or
assert), not only in a design doc. Assignment is mechanical; choosing `I` is not.

**Safety vs liveness in concurrent/async code (Huth & Ryan LTL, Ch 3).** Classify
each concurrency property before writing tests:
- *Safety* (“nothing bad ever happens”): mutex, no data race, no double-free.
  Refuted by a finite bad trace. Test with assertions, race detectors, bounded
  interleavings.
- *Liveness* (“something good eventually happens”): progress, no deadlock,
  request eventually acknowledged (`G (requested → F ack)`). Refuted only by an
  infinite postponing trace; needs fairness (a thread that is enabled infinitely
  often actually runs). Finite unit tests can miss liveness bugs — use timeouts,
  fairness assumptions, or a small model checker, not another happy-path test.
Do not treat a mutex test as a deadlock test; they are different properties.

---

## 4. Error handling

**Fail fast, catch narrow, never swallow. Encode expected failures in types,
not comments.** LLM-generated error handling is systematically weak (~63% gap
vs senior devs on exception tasks). Always write and run failure-path tests
before merging AI-generated exception blocks.

**Error strategy by language:**

| Language | Expected absence | Expected failure | Unexpected |
|---|---|---|---|
| Python | `None` return value (type: `T \| None`) | specific exception | let propagate or log+reraise |
| JS/TS | `undefined` / `null` | `throw new Error(...)` or `Result<T,E>` | never swallow |
| Go | `(T, error)` — zero value + non-nil error | `fmt.Errorf("context: %w", err)` | `panic` only on invariant bugs |
| Rust | `Option<T>` | `Result<T, E>` + `?` | `panic!` only on invariants |

**Python:**
- Raise built-ins when they fit (`ValueError` bad args, `TypeError` wrong type)
- Custom exceptions: inherit existing class, name with `Error` suffix
- Never `except:` or bare `except Exception` unless you re-raise or log+suppress
  at an isolation boundary
- Don't use `assert` for runtime preconditions (stripped with `-O`)
- Python 3.11+: use `asyncio.TaskGroup` + `ExceptionGroup` for concurrent errors
- Keep `try` bodies small; use `finally`/context managers for cleanup

```python
# yes
if port < 1024:
    raise ValueError(f'port must be >= 1024, got {port}')

# no: assert is stripped with -O; not a runtime guard
assert port >= 1024

# no: swallowing all exceptions
try:
    connect(port)
except:
    pass
```

**JS/TS:**
- `throw new Error('...')`, never `throw 'string'`
- TS: `unknown` in `catch (err)`; narrow before use (never `any`)
- For module boundaries: consider `neverthrow` (lightweight) or Effect (typed
  errors + resources, heavier). Don't mix Result-style and thrown exceptions
  on the same API boundary.
- Never leave rejected promises unhandled; `Promise.allSettled` when partial
  success is acceptable

**Go:** (see §5 Go for full rules)
- Always `fmt.Errorf("operation %s: %w", id, err)` -- wrap with `%w`, add context
- `if err != nil` is idiomatic; do not try to eliminate it
- `context.Context` is the first parameter; never store it on structs

**Rust:** (see §5 Rust for full rules)
- Libraries: `thiserror` + typed `Error`. Apps: `anyhow`. Use `?` everywhere.
- `let-else` for early reject; run Clippy in CI with `-D warnings`
- `expect("invariant: reason")` over bare `unwrap()` except in tests

**Shell:**
- `#!/bin/bash` then `set -euo pipefail` at top
- Quote always: `"${var}"`. Use `[[ ]]` not `[ ]`. `$(...)` not backticks. Never `eval`
- `local` all function vars. Run ShellCheck
- Send errors to stderr; check return values explicitly

**SQL:** never hide errors with `WHEN OTHERS THEN NULL`. Prefer DB constraints
over app-level checks. Transactions wrap all multi-statement writes.

**General:** include context in error messages (`port=22 host=db`). Don't use
exceptions as control flow. Return values for expected absence (`None`/`undefined`);
exceptions for unexpected failure.

**Retry/backoff loops: declare stopping criteria before the loop starts (Wald).**
Do not let stop conditions emerge from nested ifs, "one more try", or unbounded
`while True`. Pre-declare max attempts, timeout, and the accept/reject thresholds.
Wald: sequential procedures without absorbing boundaries (or truncation) can have
**unbounded expected cost**, especially in the indifference zone where each retry
has near-zero drift ("maybe it will work this time"). Truncate. See
`wald-sequential-analysis`.
<!-- why: Wald: unbounded sequential procedures have unbounded expected sample number when boundaries are absent or E(z)≈0 -->

---

## 5. Language-specific rules

### Python (3.11+)
- 4 spaces. Line length: 79 cols per PEP 8; 88 cols is the Black/Ruff default and widely
  adopted in practice -- follow the repo's formatter config, defaulting to 88 if none exists
- `snake_case` functions, `CapWords` classes, `UPPER_SNAKE` constants
- Use built-in generic types: `list[T]`, `dict[K, V]`, `X | None` -- not `typing.List`, `Optional`
- PEP 695 (3.12+): `class Box[T]:` and `def first[T](xs: list[T]) -> T:` instead of `TypeVar`
- `match`/`case` for tagged union dispatch; walrus `:=` only when it removes a duplicate call
- `asyncio.TaskGroup` (3.11+) for concurrent tasks -- not bare `gather` with orphan tasks
- `except*` + `ExceptionGroup` for concurrent error handling
- Comparisons: `is`/`is not` for singletons (`None`); `==` for values; never `== True`
- Type-annotate all public APIs; `pyright` or `mypy --strict` for libraries
- PEP 735: use `[dependency-groups]` in `pyproject.toml` for dev/test deps (not extras)
- Run `ruff check` + `ruff format`; don't hand-format

```python
# Before (old typing)
from typing import TypeVar, Generic, Optional, List
T = TypeVar("T")
class Box(Generic[T]):
    def get(self) -> Optional[T]: ...

# After (PEP 695, Python 3.12+)
class Box[T]:
    def get(self) -> T | None: ...

type UserId = str

# Structured concurrency
async with asyncio.TaskGroup() as tg:
    tasks = [tg.create_task(fetch(u)) for u in urls]
# ExceptionGroup raised if any fail; all tasks awaited
```

### JavaScript / TypeScript (ES2024 + TS 5.x)
- `const` default, `let` when reassigned, never `var`
- `lowerCamelCase` values/functions; `PascalCase` classes, React components, enums
- `===` always; no `==`. Trailing commas in multiline. Semicolons on.
- TS: no `any`; use `unknown` then narrow. `satisfies` for parsed JSON (not `as Type`)
- `const` type parameters (TS 5.0) for literal inference without `as const`
- `using` for explicit resource management (TS 5.2+ / ES2025 proposal)
- `Object.groupBy` / `Map.groupBy` instead of `reduce` grouping (Baseline 2024)
- No `IUser` prefix on interfaces; `interface` for object shapes, `type` for unions/aliases
- `Promise.allSettled` when partial success is OK; never leave rejected promises unhandled

```ts
// Before
const groups = items.reduce((acc, item) => {
  (acc[item.kind] ??= []).push(item);
  return acc;
}, {} as Record<string, Item[]>);
const cfg: Config = JSON.parse(raw);  // widens, loses literal checks

// After
const groups = Object.groupBy(items, (item) => item.kind);
const cfg = JSON.parse(raw) satisfies Config;
function identity<const T>(x: T): T { return x; }
```

### Go (1.22+)
- `context.Context` is always the first parameter; never store it on a struct
- `var t []string` (nil slice) not `t := []string{}` unless empty-but-non-nil semantics needed
- `fmt.Errorf("op %s: %w", id, err)` -- always wrap errors with context
- `if err != nil` is idiomatic; do not attempt to eliminate it
- `crypto/rand` for keys/tokens; never `math/rand`
- Go 1.23+: range-over-func iterators for custom sequences
- Table-driven tests; `got`/`want` convention; `gofmt` is non-negotiable
- Short names in small scope; longer at package level; `goimports` manages imports
- Naming: `camelCase` for unexported, `PascalCase` for exported; `ErrFoo` for error vars

```go
// Before
t := []string{}
func (s *Svc) Do() { s.ctx = context.Background() }

// After
var t []string
func (s *Svc) Do(ctx context.Context) error { ... }

// Error wrapping
return fmt.Errorf("load user %s: %w", id, err)
```

### Rust
- `thiserror` for library error types; `anyhow` for application error propagation
- Use `?` everywhere applicable; `let-else` for early reject
- `expect("invariant: reason")` over bare `.unwrap()` (except tests)
- `// SAFETY: ...` comment on every `unsafe` block (Microsoft Rust guidelines)
- Clippy `-D warnings` in CI; `rustfmt` defaults enforced
- Immutability by default; `mut` is the exception
- Naming: `snake_case` functions/vars, `PascalCase` types/traits, `SCREAMING_SNAKE_CASE` consts/statics

### Shell / Bash
- `#!/bin/bash` then `set -euo pipefail`
- 2-space indent; functions `snake_case() { ... }` with `{` same line; `local` everything
- `readonly UPPER_SNAKE` for constants
- Long scripts (>100 lines with non-trivial logic): use Python or Go instead
- Put logic in `main()`; last line `main "$@"`

### SQL (Holywell)
- Keywords `UPPERCASE`; identifiers `snake_case`; always `AS` for aliases
- Avoid `SELECT *` in application SQL
- River-align keywords; newline before `AND`/`OR`; indent joins
- Qualify columns (`a.title`) in multi-table queries
- Parameterized queries always -- never f-strings or string concatenation (OWASP A05:2025)

---

## 6. File and project structure

- One concern per file. Split when >300-400 lines AND mixed reasons to change
- Tests mirror source: `src/foo.py` <-> `tests/test_foo.py` (or colocated `foo.test.ts`)
- Config at repo root: `pyproject.toml` / `package.json` / `.editorconfig`
- Don't commit secrets, build artifacts, or `__pycache__`. Use `.gitignore`
- Imports: stdlib -> third-party -> local; sorted (ruff/goimports/eslint)
- SQL migrations: versioned `0001_create_users.sql`; never edit applied migrations -- add new

**Monorepo (if needed):**
- `apps/` and `packages/` separation; apps must not import from other apps
- Internal packages via workspace protocol (`workspace = true` / `"*"`)
- One lockfile, one task runner config (`turbo.json` / `nx.json`)
- Python: `uv workspaces` with PEP 735 dependency groups
- JS: `pnpm workspaces` + Nx or Turborepo for affected CI + remote cache
- Commit `AGENTS.md` at repo root (and per-package in monorepos) with formatter,
  test command, PR title format -- agents read this, not tacit style

```
repo/
  AGENTS.md         # style/test/PR rules for AI agents
  .editorconfig
  pyproject.toml    # or package.json
  src/              # or package name
  tests/
  docs/
  scripts/          # operational helpers
```

---

## 7. Testing

**Tests are the primary defect-prevention layer for AI-generated code.**
Always require tests; treat untested code as incomplete.

### Information-theoretic test value

MacKay Ch 36: a test has value only if it can change the action taken.
  - A test whose outcome you can predict with certainty before running it has zero value.
  - A test that can only confirm existing belief adds no information.
  - Conversely, a test you are uncertain about is high-value: I(outcome; belief) > 0.

Corollary: when all your tests pass, ask whether any would catch a plausible bug.
If none would, the suite is zero-value relative to the bug class you care about.

### Typical inputs are more powerful than hand-crafted ones (AEP, Cover & Thomas Ch 3)

The Asymptotic Equipartition Property says that almost all samples from a distribution
look similar (lie in the typical set of size ~2^{nH}). Hand-crafted examples are
typically atypical -- they are the easy boundary cases, not the common path.
Property-based testing exploits this: generating random inputs from the natural
distribution covers the typical set efficiently, while hand-crafted tests cover
specific rare points.

Rule: use property-based tests (Hypothesis, fast-check) for any function whose
correct behavior is specifiable as an invariant over inputs. Hand-crafted examples
are still needed for boundary conditions and regressions, but they should not be
the entire test suite.

- **Unit tests:** specific, fast, no I/O. Table-driven in Go (`got`/`want`)
- **Property-based:** Hypothesis (Python), fast-check (JS/TS) -- generate + shrink.
  Use on parsers, serializers, data transforms. Don't only example-test.
- **Contract tests:** Pact for consumer-driven API contracts before integration
- **Snapshot tests:** for serializers, UI components, NOT for business rules
  (snapshot-only tests become change-detector tests -- harmful)
- **Failure-path tests required** for all error-handling code, especially LLM-generated
- Never ship AI exception blocks without explicit tests for the failure cases
- **Property-based:** Hypothesis (Python), fast-check (JS/TS) -- generate + shrink.
  Use on parsers, serializers, data transforms. Don't only example-test.
- **Contract tests:** Pact for consumer-driven API contracts before integration
- **Snapshot tests:** for serializers, UI components, NOT for business rules
  (snapshot-only tests become change-detector tests -- harmful)
- **Failure-path tests required** for all error-handling code, especially LLM-generated
- Never ship AI exception blocks without explicit tests for the failure cases

```python
# Before: single example
assert sort([3, 1, 2]) == [1, 2, 3]

# After: property-based
from hypothesis import given, strategies as st
@given(st.lists(st.integers()))
def test_sort_ordered(xs):
    ys = sorted(xs)
    assert all(a <= b for a, b in zip(ys, ys[1:]))
```

---

## 8. Security-first conventions

- **Parameterize all queries** server-side -- client "parameterization" that concatenates is not a control (OWASP A05:2025 Injection)
- Validate at trust boundaries with allowlists, not denylists
- Go: `crypto/rand` for tokens/keys; never `math/rand`
- Docker: pin base image to digest or tag; `USER nonroot`; never `ENV`/`ARG` for secrets -- use BuildKit secret mounts
- GitHub Actions: pin to full SHA (not tag); `permissions: contents: read` default; never `pull_request_target` + untrusted checkout
- Terraform: `terraform fmt` + tflint; Kubernetes: specify resource limits, `automountServiceAccountToken: false` if unused
- Never commit secrets; `detect-private-key` pre-commit hook

```python
# no
cur.execute(f"SELECT * FROM users WHERE id = '{user_id}'")

# yes
cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
```

---

## 9. Version control

### Commit messages (Conventional Commits 1.0)

```
<type>[optional scope][optional !]: <description>

[optional body]

[optional footer(s)]
```

- Types: `feat` (MINOR), `fix` (PATCH), `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`
- Breaking: `feat!: ...` or footer `BREAKING CHANGE: ...`
- Description: imperative, lowercase after colon, no trailing period, <=50 chars (Chris Beams convention; Conventional Commits spec has no hard limit)
- Body at 72 cols; explains *why*, not *how*
- Dependabot: configure `commit-message.prefix: "chore(deps)"` so bots pass commitlint

```
# yes
feat(auth): add PKCE to the login flow

The implicit grant leaked tokens via the redirect fragment.

Refs: #1842

# no
fixed stuff.
WIP
Update file.py
```

### Branch naming

```
<type>/<description>
```

- Types: `feature`/`feat`, `bugfix`/`fix`, `hotfix`, `release`, `chore`
- Lowercase, hyphens, digits; dots only in versions (`release/v1.2.0`)
- No underscores, no leading/trailing hyphens

One logical change per commit. Don't mix refactor + feature.

---

## 10. Design principles (empirical posture)

### Information-theoretic foundations for these rules

The design principles below have formal grounding in information theory and
algorithmic complexity. These are not just aesthetics -- they have provable structure.

**MDL test for abstraction (Li-Vitanyi, Ch 5; MacKay, Ch 28).**
Minimum Description Length says the right abstraction satisfies:
  L(interface) + L(code | interface) < L(code without abstraction)
One-part minimization -- eliminating duplication by surface similarity alone -- overfits.
Do NOT extract a shared helper unless the interface description plus the
simplified usage is shorter than the two inlined copies. Coincidental similarity
fails this test. Shared invariant behaviour passes.

This is the formal basis for the DRY warning below: "apply to knowledge, not
coincidental similarity." The MDL test operationalizes it: if you cannot write a
shorter total description with the abstraction, it has negative value.

**DPI: abstraction layers lose information (Cover & Thomas, Ch 2).**
The Data Processing Inequality states I(X;Z) <= I(X;Y) for any chain X->Y->Z.
Each abstraction layer can only reduce, never increase, the information available
to the caller about the underlying implementation. Implication:
- Expose only what callers need (DPI forces a choice: every hidden detail is gone).
- Deep abstraction stacks are not "free" -- they lose information at every layer.
- A caller who needs to know how a deep abstraction works is experiencing DPI leakage:
  the abstraction boundary is in the wrong place.

**Equivocation and naming (Shannon 1948, Sec 12; Cover & Thomas, Ch 2).**
Shannon's equivocation H(X|Y) measures the reader's residual uncertainty about X
after observing Y. For a variable name Y and its intended meaning X:
  H(intent | name) >= H(Pe) + Pe * log(|meanings| - 1)  (Fano bound)
High equivocation directly lower-bounds the error rate of misuse. A name that
leaves readers uncertain about intent has a provably non-zero misuse rate.
This is the formal basis for the naming rules in section 1: names are not
aesthetic -- they are the primary information channel between code and reader.

**Logical depth and complexity hiding (Li-Vitanyi, Ch 7 -- Bennett depth).**
Bennett's logical depth measures how long it takes to decompress a short description.
Code that is short to describe but expensive to understand (deeply nested, heavily
abstracted, many indirection layers) is "deep" in this sense -- complexity is
hidden, not removed. High depth is a smell: the complexity budget still exists,
it is just deferred to the reader at runtime.
KISS is the empirical manifestation of preferring shallow over deep.

**Comments and redundancy (Shannon 1948, Sec 7).**
Shannon showed English has ~75% redundancy -- letters predictable from context carry
zero new information. Code comments that restate what the code already says have zero
mutual information with the reader's residual uncertainty. They are pure redundancy.
The rule "comment the why, not the what" has an information-theoretic basis:
  I(comment; intent) = 0 when comment = paraphrase(code)
  I(comment; intent) > 0 when comment adds non-obvious context (invariant, reason, constraint)
Stale comments that no longer match the code are actively negative information --
they increase equivocation about which source is authoritative.

**Probability as extended logic (Jaynes / Cox).** Probability is the unique consistent extension of Boolean logic under uncertainty. When a function returns a confidence, score, or "probability":
- It is a probability only if it obeys the axioms: non-negative, and sums to 1 over any exhaustive partition of outcomes. Scores that fail this must not be multiplied, thresholded as p, or fed to expected-utility arithmetic. Name them `score` / `uncalibrated_score`, never `probability`.
- **Maximum entropy:** when choosing a distribution to model uncertainty (sampling, simulation, priors), use the maximum-entropy distribution consistent with known constraints — uniform when nothing is known, Gaussian when only mean and variance are known. A more specific family without a justifying constraint is over-specification (claiming information you do not have).
- **Ad-hoc vs principled scoring:** heuristic systems that combine features with magic weights are uncalibrated. Any scoring function used for decisions should be derived from a probabilistic model, or explicitly acknowledged as uncalibrated. Do not treat a weighted sum as p(H|data).

**KISS** -- simplest thing that works. Nested cleverness is a defect.

**YAGNI** -- no parameters, layers, feature flags, or abstractions without a
caller today. Delete unused code; VCS remembers it.

**DRY -- apply to knowledge, not coincidental similarity.** Extract when the same
*behavior with one owner* is duplicated. Do NOT premature-abstract code that merely
looks similar but has different reasons to change. Warning: AI tools drive
clone/copy-paste rates up sharply (8% -> 12% of commits, 2020-2024, GitClear).
Add clone detection to AI-assisted workflows.

**Immutability and pure cores** -- the transferable win from FP. Applies inside
any paradigm. Pure functions are easier to test, cache, and reason about.

**Curry-Howard (Thompson).** A type signature is a theorem; a function body is
its proof. Types should be expressive enough to rule out wrong inputs at compile
time — narrow types over runtime checks. If a bad value type-checks, the theorem
is too weak. <!-- why: prevents under-specified signatures that push validation to runtime -->

**Correctness-by-construction (Thompson).** Design data types so invalid states
cannot be constructed (parse-don't-validate). The constructor *is* the validator.
Runtime checks after a wide constructor are a failed formation rule — encode the
invariant in the type (newtypes, enums, refined constructors) instead. <!-- why: prevents invalid states from existing and then being defended against ad hoc -->

**Totality (Thompson).** Partial functions (throw/crash on some inputs) are defects.
All cases must be handled; use Option/Result instead of exceptions for expected
failure modes. A function that is only defined on a subset should take that subset
as its type, not a wider type plus a trap. <!-- why: prevents crash-on-input as an implicit part of the contract -->

**FP vs OOP** -- no universal winner. Use FP for pipelines, error-as-value,
concurrency; OOP for domain models with identity. Standardize error style per
module (exceptions OR Result), not both.

**SOLID** -- use as heuristics, not a checklist. No strong empirical evidence that
SOLID-as-a-bundle reduces bugs. Enforce via smells (God class, feature envy) in
code review, not as mandatory architecture layers.

---

## 11. AI-assisted coding conventions

AI output is untrusted until formatter + linter + tests pass. Treat LLM code as
a new defect distribution: ~25-40% of studied samples have security issues (Fu et al.
29.5% Python / 24.2% JS in real GitHub snippets; Pearce et al. ~40% in CWE-targeted
Copilot scenarios -- different study designs, directional not a single unified rate);
error handling is systematically weak; clone/duplication rates are rising.

**Before accepting AI-generated code:**
1. Run formatter + linter (anti-drift; models frequently violate style)
2. Review for LLM-specific bugs: hallucinated APIs, prompt-biased extras,
   missing corner cases, wrong input types, incomplete generation
3. Add tests -- especially failure-path tests for exception blocks
4. Check for clones / copy-paste that should be extracted
5. **Never accept a green test suite as proof of correctness if the AI wrote both the
   code and the tests in the same context window.** Tests written by the same agent that
   wrote the code are biased toward the code's own blind spots (ExecCritic, arXiv:2609.09133:
   same-agent test+code degrades resolve rate vs separate roles). Require at least one
   independent check: spec replay, a frozen pre-existing test, or a cold reviewer.
6. **Treat reported quality rates as point estimates with wide uncertainty.** Empirical
   rates ("~25-40% of AI-generated code has security issues") come from small studies with
   different methodologies. Use these as directional bounds, not exact thresholds. Apply
   stricter review proportional to security/correctness criticality, not to a fixed rate.

**Workflow conventions:**
- Give AI context: open relevant files, close irrelevant ones
- Write intent comments before generating: `# Fetch user by id, parameterized, return None if missing`
- Commit `AGENTS.md` with formatter, test command, PR title format, no-any/no-secrets rules
- Review AI PRs for bugs and architecture -- not commas
- Track clone rate and 2-week churn as AI-quality KPIs, not LOC
- **Context locality (arXiv:2609.00148):** Re-buy rate of context already in the window is a
  measurable waste: median 24% re-retrieval per session. Before calling a retrieval tool
  (hindsight, session_search, read_file on a path already loaded, web_extract on a URL already
  fetched), scan the last 5 tool results in context first. This applies equally to AI coding
  agents: if the agent already loaded a file this session, it should not re-read it to check
  a fact that is already visible in context.

---

## 12. Code review

### The channel-capacity readability test (Gallager ITRC, Ch 5)

Gallager's random-coding bound says a good code transmits intent reliably at
any rate below channel capacity -- without the author needing to explain it.
Applied to code: the reviewer is the receiver; the code is the codeword.

Channel capacity test: a reviewer who has never seen this code should be able to
decode the intent from structure, names, and types alone -- without asking the author.
If the reviewer needs out-of-band explanation to understand what the code does or why,
the code is operating above its "channel capacity" for readability. That is a defect,
not a documentation problem.

Expurgation principle (Gallager, Ch 5): removing the worst codes from an ensemble
improves the average quality of the remaining codes. Applied to test suites and
code review: remove or refactor the most confusing functions first. The remaining
codebase is easier to review. Do not average over confusing and clear code equally;
weight defect-removal toward the highest-equivocation regions.

**Causal DAG of state mutations (Pearl).** In distributed systems and async code, draw the causal DAG of state mutations during review. Race conditions are causal DAG cycles or missing ordering edges (happens-before). If A and B both write the same state with no ordering edge, the runtime is not a DAG — do not ship until you add an ordering constraint or make the writes commute.
<!-- why: prevents shipping races that look locally consistent but have no happens-before -->

- **No unreviewed merge** to default branches (defect risk is significantly higher for
  unreviewed changes; Bavota & Russo 2015 found ~2x in one study -- treat as directional)
- Keep diffs small; large diffs kill review effectiveness
- Automate conventions (formatters, linters, bots for naming/import/API hygiene)
- Humans own: behavior, concurrency, security, data lifetime, LLM-clone risk
- Measure by defect escape rate + time-to-first-comment, not comment count
- Advisory-only for AI review bots (CodeRabbit, Copilot, etc.) -- they do not own merge
- Keep diffs small; large diffs kill review effectiveness
- Automate conventions (formatters, linters, bots for naming/import/API hygiene)
- Humans own: behavior, concurrency, security, data lifetime, LLM-clone risk
- Measure by defect escape rate + time-to-first-comment, not comment count
- Advisory-only for AI review bots (CodeRabbit, Copilot, etc.) -- they do not own merge

---

## 13. Composition, functors, monads, ADTs (Milewski)

Grounded in Milewski, *Category Theory for Programmers* (v1.3.0). Full toolkit: `milewski-category-theory`.

### Composition is a design constraint (Ch 1.2–1.3, Ch 2.2)

Morphisms compose only when types match; composition is associative and has identities. A chunk's **surface** (signature / interface) is what you need to compose it; **volume** is implementation you must forget. **Defect:** a function that is only correct if the caller knows extra context (hidden protocol, globals, "don't call until X", order-of-operations folklore) is not composable — flag it. Types exist to make that match mechanical; tests are a poor substitute for that proof.

### Functor laws on container transforms (Ch 7, Ch 7.1.2)

`fmap`/`map` must preserve identity and composition:

```
fmap id = id
fmap (g . f) = fmap g . fmap f
```

Review criterion for any `.map()` / `.filter()` chain:
- Mapped functions and filter predicates must be **pure**. Side-effecting callbacks break equational reasoning (Milewski's `square(counter())` vs `counter() * counter()`).
- `.map()` must **preserve structure** (same shape, no dropped/invented elements). `.filter()` is *not* a functor — it changes shape — do not treat it as `fmap`; still keep the predicate pure so the chain can be refactored.

### Monad / Kleisli associativity (Ch 20.1, Ch 1.2, Ch 20.3)

`Promise.then`, `flatMap`, `Result`/`Either` binds are Kleisli composition. The chain must satisfy:

```
(f >=> g) >=> h = f >=> (g >=> h)
return >=> f = f
f >=> return = f
```

If regrouping steps changes results, the combinator is not a monad — that is a source of subtle ordering bugs (same reason Writer only works when the log is a monoid). C++ futures / async continuations are this pattern; handler-calls-handler spaghetti is the failure mode.

### Algebraic sum types over sentinels (Ch 6.3–6.4)

Prefer sums (`Either`/`Maybe`, TS discriminated unions, Rust/Swift enums with data, Python `match` on tagged unions) over null-checks, empty-string/negative sentinels, and boolean mode flags. A sum contains *one* alternative; a product contains *both*. Sentinels make extra inhabitants that are not in the type's algebra.

---

## 14. ML evaluation code (Hastie ESL)

When the diff trains, tunes, or scores a model, review these before style nits.

**Bias–variance before tuning.** Decompose error before touching hyperparameters. High training error = bias (model too simple) — add capacity or relax the penalty. Large train/test gap with low training error = variance (overfit) — shrink, prune, or get data. Tuning without this diagnosis is guessing. Training error is optimistic (ESL Ch 7.4: optimism ∝ Cov(ŷᵢ, yᵢ)); a model with zero training error is overfit, not done.

**Match the regularizer to the domain prior.** L2 / weight decay is a Gaussian prior (ridge; ESL Ex 3.6). L1 is a Laplace prior and yields sparse solutions (lasso). Dense correlated effects → L2. Few large effects, rest noise → L1. Picking L1 because the library defaulted to it is a review defect. Do not penalize the intercept; standardize inputs before L2.

**Point estimates of stochastic metrics are incomplete specifications.** Accuracy, loss, latency, or any metric from a stochastic process (CV folds, bootstrap replicates, random seeds, load tests) must ship with uncertainty — bootstrap CIs or fold-wise SE bands, not a lone mean. ESL Ch 7.11: the bootstrap exists to estimate the sampling distribution of S(Z). A number without an interval cannot be compared or gated.

**Selection is part of training.** Feature screens, scalers, and λ-search belong inside each training fold. A test score computed on data that influenced selection underestimates Err (ESL 7.10.2 wrong-way CV).

---

## 15. Numerical optimization review criteria (Boyd & Vandenberghe)

Silent correctness bugs in custom optimizers, loss functions, and solvers. Load `boyd-convex-optimization` when the change is an optimizer. Review these before merge:

**Convexity before a convex solver.** Before implementing a custom optimizer, verify the objective is convex on the domain actually used: second derivative `f'' ≥ 0`, or Hessian PSD (Cholesky without pivoting succeeds iff PD). Optimizing a non-convex objective with a convex solver is a silent correctness bug, not a tuning issue. If convexity fails, do not ship a convex method as if it had global guarantees.

**Lipschitz constant before a fixed step size.** Gradient descent step size must satisfy `t ≤ 1/L`, where `L` is a Lipschitz constant of `∇f` (equivalently an upper bound `M` on `∥∇2 f∥`). Always derive or bound `L` before setting a learning rate. A fixed step without an `L` bound is a bug waiting to happen; if `L` is unknown, use backtracking line search rather than a magic constant. Shrink `t` onto `dom f` before the Armijo check when the objective is infinite outside its domain (logs, barriers, `x^2/y`).

**Duality gap as a convergence certificate.** For constrained optimization, the duality gap `f_0(x) - g(λ, ν)` certifies optimality: gap 0 (within tolerance) means the primal-dual pair is optimal; a nonzero gap means the solution is not certified. Solvers should report the duality gap. Do not treat "feasible and the objective decreased" as done.

---

## 16. Algorithmic correctness and cost (CLRS)

These are correctness and analysis rules, not style preferences. Cite CLRS when applying them. Load `clrs-algorithms` for the full statements.

### Loop invariants (CLRS 4th ed, §2.1)

Every non-trivial loop must have a documented invariant with three parts:

1. **Initialization** — the invariant holds before the first iteration.
2. **Maintenance** — if it holds before an iteration, it holds before the next.
3. **Termination** — the loop ends, and the invariant plus the exit condition imply the postcondition.

A loop-invariant proof is induction that stops when the loop exits. The invariant is the correctness argument; a comment that restates the next line is still forbidden (section 3). Nested loops need nested invariants. If you cannot state initialization, maintenance, and termination, the loop is not ready to merge.

<!-- why: CLRS §2.1 (insertion sort) treats the invariant as the proof of correctness, not as optional documentation. -->

### Amortized cost, not per-operation worst case (CLRS 4th ed, Ch 16; Ch 19)

When reviewing code that uses **dynamic arrays**, **heaps**, or **union-find**, evaluate amortized cost over a sequence, not the worst single operation.

- Dynamic tables (§16.4): doubling on insert is Θ(n) for that call and O(1) amortized; Σ copy costs is a geometric series < 2n. Do not reject `vec.push` / `ArrayList.add` / `Vec::push` because a resize is linear.
- Aggregate (§16.1): Multipop looks O(n) per call, but n stack operations are O(n) because each item is pushed at most once and popped at most once.
- Accounting (§16.2) / potential (§16.3): extra charge or Φ pays for later expensive ops; credit/Φ must stay nonnegative.
- Union-find (Ch 19): union-by-rank + path compression is O(m α(n)) for m operations, not O(n) per Find.

A Θ(n) spike does not make the API Θ(n) per call. Quote the sequence bound.

<!-- why: CLRS Ch 16 shows per-op worst case is a loose, often quadratic, overstatement for these structures. -->

---

## Agent decision loops (MDP invariants)

When writing or reviewing **agent loop / planner / policy** code, treat Puterman's MDP
results as correctness constraints, not style. See `puterman-mdp`.

**Markov property — state, not history.** Bellman optimality says the value of a state
depends only on immediate reward plus discounted expected future value — not on the path
that reached it. Any decision function that takes unbounded raw history (full trace,
growing message list, unsummarized trajectory) as its state is violating the Markov
property. Redesign with an explicit state encoding (goal, constraints, remaining budget
or horizon, last observation, belief). History may be *logged*; it must not be the
decision key.

**Finite horizon vs infinite horizon.** Finite-horizon problems require time-indexed
value functions and generally non-stationary policies (action depends on periods left).
Infinite-horizon discounted problems admit a stationary policy. Mixing these — e.g. a
stationary policy on a finite-horizon problem without putting remaining time into the
state — is a design defect, not a simplification.

**Reward shaping preserves π* only if it is potential-based.** A shaped bonus must
satisfy Ng, Harada & Russell (1999): `F(s,a,s') = γ Φ(s') − Φ(s)`. Arbitrary reward
bonuses change the optimal policy. That is a correctness bug, not a tuning issue.
If you cannot exhibit Φ, do not add the bonus.

---

## Pre-commit checklist

- Match neighboring files' naming and formatter
- Names: language table in section 1; no type suffixes; no single-letter l/O/I; no homonyms
- PEP 735 for Python dev deps; `list[T]` / `T | None` not `typing.*`
- Comment only non-obvious *why* + SATD with owner; no auto-generated narrative
- Catch specific errors; never empty `except`/`catch`; no `assert` for runtime guards
- Failure-path tests for all error-handling, especially LLM-generated
- Commits: `type(scope): imperative subject <=50 chars`; branches `type/kebab`
- Parameterized SQL; `crypto/rand` for secrets; SHA-pinned Actions; nonroot Docker
- AGENTS.md committed; formatter config committed; pre-commit hooks pinned to tags
- Optimizer / loss / solver: convexity checked (Hessian PSD or `f''≥0`); GD step `t≤1/L` or backtracking; constrained solvers report duality gap
- ML diffs: bias vs variance diagnosed before tuning; L1/L2 matched to prior; metrics have intervals; no wrong-way CV
- Functions compose through their types; caller-context-only correctness is a design defect (Milewski Ch 1.3)
- `.map()` callbacks pure + structure-preserving; no effects in `.map()`/`.filter()` chains (Ch 7.1.2)
- `then`/`flatMap`/`Result` chains associative; prefer sum types over null/sentinels (Ch 20.1, Ch 6.3)

---

## Sources (2025-2026)
- PEP 8: https://peps.python.org/pep-0008 | PEP 257: https://peps.python.org/pep-0257
- PEP 695 (type params): https://peps.python.org/pep-0695
- PEP 735 (dep groups): https://peps.python.org/pep-0735
- Google Style Guides: https://google.github.io/styleguide
- Microsoft Rust Guidelines: https://microsoft.github.io/rust-guidelines/
- Airbnb JS: https://airbnb.io/javascript | StandardJS: https://standardjs.com
- Conventional Commits: https://www.conventionalcommits.org
- SQL style guide: https://www.sqlstyle.guide
- OWASP Top 10 2025 / Query Parameterization: https://owasp.org/Top10/2025
- Ruff: https://docs.astral.sh/ruff | Biome: https://biomejs.dev | Oxlint: https://oxc.rs
- Go Code Review Comments: https://go.dev/wiki/CodeReviewComments
- Rust API Guidelines: https://rust-lang.github.io/api-guidelines
- Effect.ts: https://effect.website | neverthrow: https://github.com/supermacro/neverthrow
- Hypothesis: https://hypothesis.readthedocs.io | fast-check: https://fast-check.dev
- GitClear 2025 AI Code Quality: https://gitclear.com/helping_organizations_with_ai
- Wong et al. naming (arXiv:2507.18081) | Le et al. obfuscation (arXiv:2510.03178)
- Oliveira et al. formatting SLR (arXiv:2208.12141) | Dantas et al. readability (arXiv:2309.02594)
- Fu et al. Copilot security (arXiv:2310.02059) | Tambon et al. LLM bugs (arXiv:2403.08937)
- Selvanayagam et al. LLM SATD (arXiv:2601.06266) | Li et al. PRESTI (arXiv:2309.06020)
- Vijayvergiya et al. AutoCommenter (arXiv:2405.13565)
- SO Developer Survey 2025: https://survey.stackoverflow.co/2025
- Milewski, Category Theory for Programmers v1.3.0 (Ch 1, 2, 6, 7, 20): composition/functor/monad laws, ADTs

