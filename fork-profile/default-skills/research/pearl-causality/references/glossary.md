# Pearl causality — glossary

**Autonomy** — each structural equation is an independent mechanism; intervening on one does not rewrite others (Ch 1.4).

**Back-door criterion** — Z admissible for X → Y if (i) no node in Z is a descendant of X and (ii) Z blocks every path from X to Y with an arrow into X (Def 3.3.1). Then P(y \| do(x)) = Σz P(y \| x,z) P(z).

**Causal Bayesian network** — DAG compatible with the family of interventional distributions P*; parents are direct causes; P(vi \| pai) invariant to interventions not involving Vi (Def 1.3.1).

**Causal effect** — P(y \| do(x)): distribution of Y after deleting equations for X and setting X=x (Def 3.2.1). Not P(y \| x).

**Chain** — X → Z → Y. Conditioning on Z blocks the path.

**Collider (inverted fork)** — X → Z ← Y. Path is blocked until you condition on Z or a descendant of Z (Def 1.2.3). Selection bias / Berkson / explaining-away.

**Confounder** — common cause of treatment and outcome (fork). Confounding is not a statistical property; there is no statistical test for it (Ch 6).

**Counterfactual Y_x(u)** — value Y would take in unit u had X been x. Computed by abducting U, then surgery, then prediction (Ch 7).

**d-separation** — graphical blocking of paths (Def 1.2.3). Implies conditional independence in every distribution compatible with G (Thm 1.2.4).

**do(x) / intervention** — replace the mechanism for X with X=x; delete arrows into X. Seeing ≠ doing.

**do-calculus** — three graphical rules that reduce interventional queries to observational ones when identifiable (Thm 3.4.1). Complete for identification.

**Fork** — X ← Z → Y. Z is a confounder; condition on Z to block.

**Front-door criterion** — mediator set Z intercepts all directed X	o Y paths, with no open back-door X—Z and X blocking Z—Y back-doors (Def 3.3.3).

**Identifiability** — causal quantity uniquely determined by the observational distribution given the graph (Def 3.2.3–3.2.4). Graph property, not sample-size property.

**M-bias** — conditioning on a collider that sits between two otherwise independent background causes, opening a spurious back-door.

**Potential outcome Y_x** — Neyman–Rubin notation equivalent in intent to P(Y=y \| do(x)).

**SCM / structural causal model** — Xi = fi(PAi, Ui); each variable has one assignment; subsets remain valid under intervention (Ch 1.4, 7.1).

**Simpson's paradox** — association reverses under stratification. Resolve by the DAG: confounder vs mediator vs collider, not by a statistical default (Ch 6).

**Twin network** — two copies of the causal graph sharing U, used to evaluate nested counterfactuals (Ch 7.1.4).
