---
name: wave21b-routing-bandits
description: "Use when Wave 21B routing/bandits/online."
version: "1.0"
author: hermes-fork
license: MIT
tags: [wave21b, routing, bandits, online-learning, adversarial]
metadata:
  hermes:
    tags: [wave21b, routing, bandits, online-learning]
    related_skills: [hermes-fork-script-development, lattimore-bandit-algorithms, borodin-elyaniv-online-computation]
---

# Wave 21B routing / bandits / online learning

## When to Use

Wave 21B PAC-Bayes, EXP3/EXP4, Fano, Möbius, KL-UCB, Tsallis-INF, LinUCB, token influence, skill-graph percolation, loopy BP, or routing alarm bridging.

Canonical: `~/.hermes/hermes-scripts/`. Wrappers: `profiles/fork/scripts/`.

```bash
HERMES_HOME=~/.hermes HERMES_PROFILE=fork python3 ~/.hermes/hermes-scripts/<script>.py --self-test
```

Do **not** duplicate skill-router-index, routing-weight-updater, skill-beta-feedback, bps-skill-selector.

| Script | Theorem | Output |
|---|---|---|
| routing-pac-bayes-bound.py | McAllester PAC-Bayes | cache/routing-pac-bayes.json |
| routing-graph-bandit-update.py | Lattimore Ch 22; 0.5^hop | skill-beta-state.json |
| routing-exp3-adversarial.py | Auer EXP3 | routing-exp3-state.json |
| routing-exp4-contextual.py | EXP4 contextual | routing-exp4-state.json |
| routing-kl-ucb.py | KL-UCB Thm 10.6 | routing-kl-ucb.json |
| routing-tsallis-inf.py | Tsallis-INF BoBW | routing-tsallis-inf.json |
| routing-linucb.py | LinUCB ridge | routing-linucb.json |
| routing-fano-bound.py | Fano inequality | routing-fano-bound.json |
| routing-mobius-audit.py | Stanley Möbius | routing-mobius-audit.json |
| routing-hamming-audit.py | Jaccard < 0.3 | routing-hamming-alarm.json |
| skill-description-entropy.py | H < 2.5 bits/char | skill-description-entropy.json |
| routing-rademacher-bound.py | Shalev Ch 26 | routing-rademacher-bound.json |
| routing-boolean-influence.py | O'Donnell influence | routing-boolean-influence.json |
| routing-skill-percolation.py | Hofstad giant | routing-skill-percolation.json |
| routing-belief-propagation.py | Mézard/Wainwright BP | routing-belief-propagation.json |
| routing-precision-recall.py | Manning P@k | routing-precision-recall.json |
| skill-composition-gf.py | Flajolet GF | skill-composition-gf.json |
| routing-mcdiarmid-bm25.py | McDiarmid | routing-mcdiarmid-bm25.json |
| routing-token-setcover.py | Vazirani greedy cover | routing-token-setcover.json |
| routing-skill-markov.py | Jurafsky bigram | routing-skill-markov.json |
| routing-alarm-bridge.py | dark-output close | *-alarm.json |

## Lessons
- Cron graph-bandit without --skill must default from_delta so credit actually propagates.
- EXP3 writes both routing-exp3-skill-weights.json and routing-exp3-state.json (spec name).
- alarm-aggregator only globs *-alarm.json; bridge promotes other routing JSON `alarm` flags.
- PAC-Bayes prior is uniform; posterior is normalized beta means; KL in pure Python.
- Do not average BP beliefs across RSB modes; alarm instead.
