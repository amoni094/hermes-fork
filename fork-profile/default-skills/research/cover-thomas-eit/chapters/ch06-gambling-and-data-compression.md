# Chapter 6: Gambling and Data Compression

## Core Idea
In a horse race, the optimal (Kelly / proportional) gambler’s wealth growth rate plus the entropy rate of the race equals the log of the odds product; side information is worth exactly its mutual information in growth-rate bits. A good gambler is a good compressor, which yields a gambling estimator of the entropy of English.

## Key Concepts
- **Horse race**: horse i wins with p_i; payoff o_i-for-1 (stake 1 returns o_i if i wins, else 0).
- **Betting vector** b = (b1,...,bm), b_i ≥ 0, ∑ b_i = 1 (all-in each race).
- **Wealth**: S_n = ∏_{k=1}^n b_{X_k} o_{X_k}; doubling rate W(b,p) = E log S = ∑ p_i log(b_i o_i).
- **Kelly/proportional betting**: b_i^* = p_i, independent of the odds.
- **Doubling rate** W^*(p) = ∑ p_i log o_i − H(p). For even odds o_i=m, W^* = log m − H(p).
- **Side information Y**: increment ΔW = I(X;Y) when odds are fair in an appropriate sense; in general ΔW ≤ I(X;Y).
- **Entropy of English**: Shannon guessing / Cover–King gambling estimates ~1.3 bits/character (order-of-magnitude; depends on model).

## Frameworks and Methods
- **Maximize E log wealth, not E wealth**: E S is maximized by betting everything on the horse maximizing p_i o_i — and then you go broke a.s. if that horse is not certain. Kelly criterion is the a.s. growth-rate optimum.
- **Information = increment in doubling rate**: causal side information raises W by at most I.
- **Gambler-as-compressor**: two identical Kelly gamblers, one seeing the sequence, can encode by the log of the wealth ratio; compression length ≈ n log m − log S_n.
- **Entropy estimation without a model**: if you can gamble well on English, your achieved W estimates H ≈ log |alphabet| − W.

## Key Results and Theorems

**Proportional gambling optimality.** For a single race,
W(b,p) = ∑ p_i log(b_i o_i) ≤ ∑ p_i log(p_i o_i) = ∑ p_i log o_i − H(p),
with equality iff b=p. Proof: W(p)−W(b) = D(p||b) ≥ 0.

**Fair odds / uniform book.** If o_i = 1/r_i with r a bookmaker distribution, W^* = D(p||r). If o_i=m (even money m-horse race), W^* = log m − H(p).

**Asymptotic growth.** For i.i.d. races, (1/n) log S_n^* → W^* a.s. (SLLN). So S_n^* ≐ 2^{n W^*}.

**Side information.** If Y is available to the gambler,
ΔW := W^*(X|Y) − W^*(X) = I(X;Y)
in the horse-race (Kelly) setting of Cover–Thomas §6.2 — the financial value of Y is I(X;Y) bits per race. (Causal / dependent races: replace I by the directed information / entropy-rate drop.)

**Dependent races.** For a stationary race process, optimal growth is log-odds rate minus entropy rate H(X).

**Theorem (gambling and compression duality).** A sequential Kelly scheme with estimated probabilities q_i induces a prefix code of length roughly −log q(x^n); wealth S_n = 2^{n log m} 2^{−l(x^n)} in the even-odds picture. Minimizing description length ≡ maximizing wealth.

**Entropy of English.** Shannon’s 26-letter+space guessing game; Cover–King sequential gambling. Estimates typically 1–1.5 bits/character for English text (far below log 27 ≈ 4.76), proving huge redundancy.

## Key Equations
- S = b_X o_X,  W(b,p) = ∑ p_i log(b_i o_i)
- b^* = p,   W^* = ∑ p_i log o_i − H(p)
- W^*(p) − W(b,p) = D(p||b)
- ΔW = I(X;Y)  (horse race with side information)
- H(English) ≈ log 27 − W_gambling

## Worked Example
m=2 horses, p=(1/2,1/2), even odds o=(2,2). Then H=1, W^*=0: you cannot grow. If p=(0.7,0.3), H≈0.881, W^*=1−0.881=0.119 bits/race (wealth × 2^{0.119} per race). If you stubbornly bet b=(1/2,1/2), W=0, leaving D(p||b)≈0.119 on the table.

Side information that reveals the winner: I(X;Y)=H(X), ΔW=H(X), new W^* = ∑ p_i log o_i = log 2 = 1, i.e. you double every race — as you should.

## Anti-patterns
- **Maximizing expected payoff E[S]**: bang-bang bets, ruin with probability 1 in repeated play.
- **Betting the odds, not the probabilities**: b_i ∝ o_i^{-1} is the bookmaker’s distribution, optimal only if p equals that.
- **Ignoring dependence**: entropy rate, not H(X1), prices a sequence of races.
- **Treating ΔW = I as universal for stock markets**: in markets (Ch 16) one only gets ΔW ≤ I(X;Y).
- **Over-interpreting English entropy numbers**: they are operational estimates under a human gambler / n-gram model, not a theorem.

## Key Takeaways
1. Kelly proportional betting is log-optimal; the gap to any other b is D(p||b).
2. Growth rate + entropy rate is conserved (given odds).
3. Side information is worth its mutual information in the horse race.
4. Compression and gambling are the same optimization.
5. English is highly redundant; entropy ≪ log|alphabet|.

## Connects To
- **Ch 5**: same objective −∑ p log q.
- **Ch 11**: D(p||q) as a rate function; gambling estimates are likelihoods.
- **Ch 13**: universal gambling ↔ universal coding.
- **Ch 14**: universal probability P_U and universal gambling.
- **Ch 16**: stock market is the vector-odds generalization; log-optimal portfolios.
