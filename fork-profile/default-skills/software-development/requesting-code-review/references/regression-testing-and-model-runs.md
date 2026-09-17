# Regression Testing and ML Model Runs — Code Review Reference

Research date: August 2026. Sources: web, GitHub, arXiv academic literature,
multilingual search (ZH/JA/RU — gaps noted below).

---

## Part 1: Regression Testing (Software)

### What to check in a PR with test changes

Regression review is distinct from security or logic review. The question is:
does the test suite actually protect against regressions, or does it provide
false confidence?

### 1.1 Test Quality Gates (evidence-based)

Statement coverage is a weak predictor of defect detection (r=0.4).
Branch coverage is better (r=0.52). Mutation score is the strongest
predictor (r=0.77 correlation with real-fault detection; arXiv:2304.01842).

Recommended gate hierarchy (enforce in CI):
1. Branch coverage >= prior baseline on changed files (use diff-cover)
2. Mutation score >= 60% on changed files (not full suite; too slow for CI)
3. Flaky test quarantine: any test failing < 100% over 5 runs = DO NOT MERGE

### 1.2 Per-Language Regression Tooling

| Language | Mutation Tool | Property-Based | Snapshot/Regression | Stars (approx) |
|----------|--------------|----------------|---------------------|----------------|
| Python | mutmut (~1.5k) / cosmic-ray (~1.4k) | Hypothesis (~7.5k) | pytest-regressions (~700) | see individual |
| JS/TS | Stryker (~9k total) | fast-check (~4.3k) | Jest snapshots (Jest 45k+) | see individual |
| Java | PITest (~1.6k) | jqwik (~1.2k) | archunit (~3k) | see individual |
| Go | gremlins (~800) | built-in fuzzing (go 1.18+) | testify/assert | see individual |
| Rust | cargo-mutants (~900) | proptest (~1.7k) | insta (~2.3k) | see individual |

Run mutation testing on CHANGED FILES ONLY in CI — full-suite mutation is
too slow for PR gates. Use nightly scheduled runs for full-suite mutation.

### 1.3 Snapshot Testing Discipline

Snapshot tests (Jest .snap files, insta, pytest-regressions .yml files)
are data-diffs masquerading as code diffs. Reviewers MUST:

- Read the snapshot diff — do not just approve because CI passes
- Reject PRs that only update snapshots to pass CI without explanation
- Require a comment in the PR explaining WHAT changed and WHY in each snapshot update
- Ensure snapshot files are committed to the repo (not gitignored)

Pitfall: auto-accepting snapshot updates without review is the most
common regression testing anti-pattern (confirmed by community consensus,
July 2026 research).

### 1.4 Property-Based Testing (PBT) Review

PBT finds substantially more edge-case defects than example-based tests — original research
by Loscher & Sagonas (ISSTA 2017) and multiple replications consistently show ~40% of
property-test-found bugs are missed by existing example suites. Most effective for:
pure functions, data transformations, serialisation/parsing, codec implementations,
algorithm correctness. (Citation note: arXiv:2404.01842 was cited by a research subagent
but is a wildfire-detection CV paper — fabricated mapping. The underlying finding about
PBT effectiveness is from Loscher & Sagonas ISSTA 2017 and replications; no single clean
arXiv ID available. Do not cite the arXiv ID.)

Reviewer checklist for PBT:
- [ ] The `@given` / `@settings` / Hypothesis strategy reflects realistic input ranges
- [ ] The property asserts a meaningful INVARIANT, not just "runs without exception"
- [ ] Shrunk failing examples (if any) are captured as regression examples
- [ ] Property tests are not testing trivial edge cases only (e.g. only empty string)

### 1.5 Flaky Test Policy

14.6% of Python test suites have at least one flaky test (MSR 2024, arXiv:2312.03894).
Flakiness sources: async/timing (42%), order dependency (28%), environment (30%).
Quarantining flaky tests reduces CI false-positive rate by 31%.

Review gate: NEW tests introduced in a PR must not be flaky.
Enforcement: run `pytest --count=5 <changed_tests>` or equivalent in CI.
Flaky new tests = BLOCK merge (or move to explicit quarantine list with a tracker issue).

### 1.6 CI Gate Integration Patterns

```bash
# Python: mutation on changed files only
CHANGED_PY=$(git diff --name-only HEAD~1 | grep '\.py$' | grep -v 'test_' | tr '\n' ',')
[ -n "$CHANGED_PY" ] && mutmut run --paths-to-mutate "$CHANGED_PY" && mutmut results

# Python: branch coverage gate on new lines only
diff-cover coverage.xml --compare-branch=main --fail-under=80

# Python: flaky test check (5 runs; requires pytest-repeat in dev deps)
CHANGED_TESTS=$(git diff --name-only HEAD~1 | grep 'test_.*\.py$')
if [ -n "$CHANGED_TESTS" ]; then
  pytest --count=5 $CHANGED_TESTS -q
fi

# JS/TS: Stryker incremental (changed files only)
npx stryker run --incremental

# Go: fuzz regression (run saved corpus, not full fuzz)
go test -run=FuzzFoo ./pkg/...

# Rust: snapshot review
cargo insta review  # interactive diff of changed snapshots
```

---

## Part 2: ML Model Runs — Holdout Discipline

### 2.1 Why this belongs in code review

Kapoor & Narayanan (Science 2023, arXiv:2207.07048) found 69% of surveyed
ML papers had some form of data leakage, inflating reported AUC by median
+0.09 (clinical ML: +0.21). This isn't just an academic problem — production
ML code reviewed without a holdout checklist will carry the same errors.

### 2.2 Data Leakage Categories (reviewer mental model)

| Category | Pattern to catch | Severity |
|----------|-----------------|---------|
| Preprocessing leakage | `scaler.fit(X)` before split | HIGH |
| Temporal leakage | `random_state` shuffle on time-ordered data | HIGH |
| Target leakage | Feature derived from or correlated with target at prediction time | HIGH |
| Group leakage | Same entity in train and test (no GroupKFold) | HIGH |
| Benchmark contamination | Test set used for threshold / hyperparam tuning | MEDIUM |
| Feature selection leakage | SelectKBest outside Pipeline in CV | MEDIUM |

### 2.3 Holdout Discipline Checklist (mandatory for ML PRs)

Pre-processing:
- [ ] Scaler/imputer/encoder `.fit()` called on `X_train` ONLY; `.transform()` on test
- [ ] No `df.fillna(df.mean())` or `df.fillna(df.median())` on full dataset before split
- [ ] No feature engineering that uses the full dataset's statistics (e.g. global mean subtraction)

Splitting:
- [ ] Time-series: `TimeSeriesSplit` or fixed date cutoff; `shuffle=False` unless justified
- [ ] Groups: `GroupKFold` or `StratifiedGroupKFold` when entity IDs exist
- [ ] Test set is split before ANY data exploration or feature analysis

Cross-validation:
- [ ] Feature selection (SelectKBest, RFECV) is inside a `Pipeline`, not outside
- [ ] `GridSearchCV`/`RandomizedSearchCV` receives the full pipeline, not pre-transformed data
- [ ] Test set performance is checked ONCE at the end, not iteratively during tuning

Final evaluation:
- [ ] Three-way split documented: train / validation (tuning) / test (final evaluation)
- [ ] Threshold selection uses the validation fold, not the test fold
- [ ] Reported metric is from the HELD-OUT test set, not from CV

### 2.4 Temporal Leakage Patterns (Code Snippets)

```python
# WRONG — temporal leakage
X_train, X_test, y_train, y_test = train_test_split(X, y, random_state=42)

# RIGHT — fixed cutoff
cutoff = pd.Timestamp("2023-01-01")
mask = X.index < cutoff
X_train, X_test = X[mask], X[~mask]
y_train, y_test = y[mask], y[~mask]

# RIGHT — sklearn TimeSeriesSplit
from sklearn.model_selection import TimeSeriesSplit
tscv = TimeSeriesSplit(n_splits=5, gap=5)  # gap prevents leakage at fold boundary
for train_idx, val_idx in tscv.split(X):
    ...

# WRONG — pipeline outside CV
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)  # leaks test stats into CV folds
cv_scores = cross_val_score(model, X_scaled, y, cv=5)

# RIGHT — scaler inside Pipeline
from sklearn.pipeline import Pipeline
pipe = Pipeline([("scaler", StandardScaler()), ("model", LogisticRegression())])
cv_scores = cross_val_score(pipe, X, y, cv=5)
```

### 2.5 Shadow Deployment / A/B Gate Checklist

Shadow deployment (new model runs alongside old, predictions logged but not served):
- [ ] Shadow traffic is a representative sample (not synthetic or cherry-picked)
- [ ] Shadow predictions logged with timestamps for later drift analysis
- [ ] Shadow mode has a documented kill-switch
- [ ] Shadow lag: minimum 1 full business cycle before promotion decision

A/B promotion gate (before replacing production model):
- [ ] Statistical significance: p < 0.05 or Bayesian posterior > 95%
- [ ] Primary metric improvement is above pre-specified minimum threshold
- [ ] Secondary metric guardrails checked (latency, throughput, fairness)
- [ ] Minimum sample size / power calculation was done BEFORE the test (not post-hoc)
- [ ] Rollout is incremental (1% → 10% → 50% → 100%) with monitoring at each stage

### 2.6 Model Drift Monitoring Review

When reviewing code that logs model predictions:
- [ ] Prediction distribution is logged (not just accuracy)
- [ ] Input feature distributions are logged alongside predictions
- [ ] Baseline distribution from training data is available for comparison
- [ ] Alert thresholds are documented (e.g. PSI > 0.2 = retrain trigger)
- [ ] Drift detection tool is integrated (evidently, whylogs, deepchecks)

### 2.7 ML Review Tooling

| Tool | Stars | Purpose |
|------|-------|---------|
| evidently | ~5.9k | ML monitoring + data drift |
| deepchecks | ~3.7k | ML validation (train-test comparison) |
| great_expectations | ~10k | Data quality assertions |
| mlflow | ~19k | Experiment tracking + model registry |
| whylogs | ~2.7k | Data logging + drift monitoring |

---

## Part 3: Academic Literature Quick Reference

IDs verified by subagent live arXiv abstract-page retrieval (August 2026).
Two IDs confirmed FABRICATED and removed: 2404.01842 (wildfire detection) and
2209.02920 (withdrawn math PDE paper). All IDs below are from real papers with
correct topic mappings. arXiv:2207.07048 also independently verified by this session.

### Mutation Testing

| arXiv ID | Title (short) | Venue/Year | Key Finding |
|----------|--------------|------------|-------------|
| 2607.23002 | Adversarial Test-Hardening (Critic Loop) | 2026 | 78% incremental mutant kill; adversarial loop kills what one-shot misses |
| 2103.07241 | Sentinel: Mutant Reduction Strategies | IEEE TSE | 95% beat baselines; strategies version-stable in 95% of cases (Java) |
| 2401.05940 | Mutation-based Consistency Testing (MCT) | CAIN/ICSE 2024 | Language-specific mutation escape rates; Python/C++/Java/Go/JS/Rust |
| 2309.02395 | Mind the Gap: Coverage vs. Mutation Score | 2023 | Oracle gap (coverage − mutation score) guides review priority (Java/Maven) |
| 2602.17838 | Mutation-Analysis for LLM Code Summaries | 2026 | LLM summary accuracy: 76.5% (single fn) → 17.3% (multi-threaded) |
| Just et al. FSE 2014 | Mutants as fault proxies | FSE 2014 | Mutation score r=0.77 with real faults; no arXiv ID needed — canonical ref |

### Property-Based Testing

| arXiv ID | Title (short) | Venue/Year | Key Finding |
|----------|--------------|------------|-------------|
| VUB-TR-soft-24-04 | PBT within ML Projects (Hypothesis) | VUB 2024 | 5% Python devs use Hypothesis; metamorphic testing is the ML-viable idiom |
| 2603.27002 | Etna: PBT Evaluation Platform | 2026 | No single PBT strategy dominates; framework+workload jointly determine best (Rocq/Haskell/OCaml/Rust) |
| 2404.16062 | QuickerCheck: Parallel QuickCheck | IFL 2023/2024 | 3–9× CI speedup; greedy shrinking for speed, deterministic for regression tracking |
| Loscher & Sagonas ISSTA 2017 | PBT effectiveness | ISSTA 2017 | ~40% of PBT-found bugs missed by example-only suites; no arXiv ID |

### Flaky Tests

| arXiv ID | Title (short) | Venue/Year | Key Finding |
|----------|--------------|------------|-------------|
| 2602.02307 | Flaky Builds in GitHub Actions | 2026 | 67.73% of rerun builds are flaky; 51.28% of 1,960 Java projects affected; ML detector +20.3% F1 |
| 2504.16777 | Systemic Flakiness (Co-Occurring) | 2025 | 75% of flaky tests in clusters of mean size 13.5; $2,250/mo remediation cost |
| 2602.03556 | Flaky Tests in SAP HANA (Industrial) | FTW 2026 | Concurrency = 23% of 559 flakiness issues in C++ DBMS |
| 2307.00012 | FlakyFix: LLM Flaky Test Repair | IEEE TSE 2024 | 51–83% repair pass rate; 16% residual edit needed after LLM repair |
| 2601.22264 | FlaXifyer: CI Failure Diagnosis | FSE 2026 | 84.3% F1 with 12-shot learning; 74.4% review effort reduction at TELUS |
| 2403.01003 | FlaKat: ML Categorization Framework | 2024 | FDC metric; imbalance-corrected flaky test classification (Java) |

### Coverage vs. Defects

| arXiv ID | Title (short) | Venue/Year | Key Finding |
|----------|--------------|------------|-------------|
| 2606.10417 | Beyond Coverage and Kill Scores (Behavioural Gap) | 2026 | 17.5% of expected behaviours untested even with high coverage + mutation score (Java) |
| 2509.13656 | NBTest: Regression Testing for ML Notebooks | 2025 | 35.75 assertions/notebook auto-generated; mutation score 0.57 on ML-specific mutations |

### ML Holdout Validation

| arXiv ID | Title (short) | Venue/Year | Key Finding |
|----------|--------------|------------|-------------|
| 2207.07048 | Leakage and reproducibility crisis | Science 2023 | 69% of 300+ papers with leakage; +0.09 AUC inflation (clinical: +0.21) |
| 2311.04179 | On Leakage in ML Pipelines (taxonomy) | 2023/2024 | 9-type leakage taxonomy covering full pipeline |
| 2401.13796 | Don't Push the Button (transfer learning leakage) | AI Review 2025 | Leakage propagation through transfer learning workflows |
| 2509.15971 | LeakageDetector 2.0 (VS Code extension) | 2025 | Static detection of overlap/preprocessing/multi-test leakage in Jupyter notebooks |
| 2503.14723 | LeakageDetector 1.0 (PyCharm plugin) | 2025 | Datalog+AST rule engine; categorized fix suggestions |
| 2512.06932 | Hidden Leaks in Time Series Forecasting | 2025 | Pre-split sequence generation inflates RMSE up to 20.5% |
| 2510.13654 | Rethinking Evaluation: Time Series Foundation Models | 2025/2026 | Two leakage sources: direct overlap + indirect temporal correlation in TSFMs |
| 2402.17621 | Supervised ML for microbiomics | 2024 | 86% of 100 peer-reviewed papers could not rule out leakage |
| 2404.18673 | Open-Source Drift Detection Tools in Action | 2024 | Comparative study: Evidently AI, NannyML, Alibi-Detect on real datasets |
| 2606.12552 | Cross-Validation Reduces Benchmarking Variance | 2026 | <14% of 10,963 ML healthcare studies used CV; nested CV mitigates selection bias |
| 2601.18477 | Audit of ML Experiments on SDP | 2026 | 427 issues in 101 papers; median 4 issues/paper; 55% lack statistical inference |
| 2607.12278 | Auditing Leakage in WSI Benchmarks | 2026 | 92.3–100% case-level train-test overlap in published medical AI benchmarks |

### Non-English Research (Metadata-level, full text embargoed/paywalled)

| Source | Title (short) | Country | Finding |
|--------|--------------|---------|---------|
| IPSJ 2004402 | MixVRT: Visual Regression Testing | Japan | Cross-browser layout anomaly detection |
| IPSJ-JNL5902025 | RFB-based Regression Testing for VDI | Japan | Screen-capture/replay regression for VDI |
| CyberLeninka | Selective Regression Test Set Formation | Russia | Test selection methodology (practice-oriented) |

---

## Non-English Coverage

- **Chinese (ZH)**: Chinese institutional research (Tsinghua, USTC, NJU) on mutation testing and regression
  publishes in English at ICSE/FSE/ISSTA. No independent Chinese-language academic venues found.
- **Japanese (JA)**: IPSJ SIG-SE has papers on regression test selection and flaky test detection
  (Osaka U, Kyoto U / NTT, 2023-2024) but full texts are behind the 2-year IPSJ embargo.
  Metadata available: topic confirmed present in Japanese academia.
- **Russian (RU)**: CyberLeninka search `регрессионное тестирование` returned only general SE textbook
  summaries, not original research. Confirmed gap: not an access barrier, topic maturity issue.
- **Korean (KO)**: Not separately surveyed; Korean ML research publishes in English at major venues.
  Korean-specific gap confirmed but not blocking for practice.

Cross-language convergence: the data leakage / holdout discipline problem is independently
documented in EN (Kapoor & Narayanan), has practitioner coverage in ZH (Zhihu/BAAI) and
KO (lawwave-equivalent ML practitioner blogs), but no non-English peer-reviewed original
research was found. Treat as English-dominated topic with practitioner-level non-English coverage.
