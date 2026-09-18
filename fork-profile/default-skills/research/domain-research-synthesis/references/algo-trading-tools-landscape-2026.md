# Algorithmic Trading Tools Landscape — Verified July 2026

*Star counts as of July 2026. Not financial advice.*

---

## Backtesting Frameworks

| Tool | Stars | Language | License | Category |
|------|-------|----------|---------|----------|
| Freqtrade | ~48,100 | Python | GPL-3.0 | Bot + backtest + ML optim |
| Backtrader | ~21,000 | Python | GPL-3.0 | Event-driven backtest + live |
| Backtesting.py | ~8,100 | Python | AGPL-3.0 | Lightweight single-instrument |
| VectorBT | ~8,275 | Python | Fair Code (BSL) | Vectorized, fast sweeps |
| NautilusTrader | ~11,000 | Rust/Python | LGPL-3.0 | Production-grade, Rust-native |
| bt (backtest) | ~2,800 | Python | MIT | Portfolio-level, rebalancing |
| QuantConnect/LEAN | ~9,700 | C#/Python | Apache-2.0 | Institutional multi-asset |
| Zipline (original) | ~19,300 | Python | Apache-2.0 | Classic; inactive since Quantopian close |
| zipline-reloaded | ~2,400 | Python | Apache-2.0 | Community-maintained Zipline fork |

### Selection guide
- **Quickest prototype**: Backtesting.py — minimal code, beautiful Bokeh charts
- **Crypto bot + live**: Freqtrade — most complete with ML optimisation, Telegram, web UI
- **Speed / parameter sweep**: VectorBT — 100–1000× faster than event-driven
- **Multi-asset institutional**: QuantConnect/LEAN — equities, options, futures, crypto
- **Production serious**: NautilusTrader — Rust-native, deterministic, backtest-live parity
- **ASX + IBKR live**: Backtrader + ib_insync combo is common

---

## Portfolio Optimization

| Tool | Stars | Language | License | What it does |
|------|-------|----------|---------|-------------|
| PyPortfolioOpt | ~5,839 | Python/Jupyter | MIT | Efficient Frontier, Black-Litterman, HRP |
| Riskfolio-Lib | ~4,339 | Python/C++ | BSD-3 | CVaR, CDaR, HRP, HERC, factor models |
| mlfinlab | ~4,842 | Python | N/A | ML tools from de Prado book |
| cvxportfolio | ~1,234 | Python | Apache-2.0 | Transaction-cost-aware optimization |
| deepdow | ~1,131 | Python | MIT | Deep learning portfolio optimization |

### Selection guide
- **Standard Markowitz/HRP**: PyPortfolioOpt — most accessible, well-documented
- **Advanced risk measures**: Riskfolio-Lib — CVaR, tail risk, constraint-based
- **Incorporating transaction costs**: cvxportfolio — convex optimization with realistic costs
- **ML/research academic**: mlfinlab (some features paywalled now)

---

## Analytics & Data

| Tool | Stars | Language | Category |
|------|-------|----------|----------|
| OpenBB Terminal | ~41,000 | Python | Research/data platform |
| yfinance | ~14,000 | Python | Free market data |
| Microsoft Qlib | ~15,000 | Python/Cython | AI quant research |
| FinRL | ~12,000 | Python | Deep RL trading |
| QuantStats | ~5,000 | Python | Portfolio analytics/tearsheets |
| FinGPT | ~14,000 | Python | LLM for finance |

### Key notes
- **OpenBB**: ASX support via .AX suffix; now also has MCP server integration
- **yfinance**: Use `ticker.AX` format for ASX; free but not production-grade
- **QuantStats**: Input a returns series, get full HTML tearsheet with Sharpe, drawdown, etc.
- **Qlib**: Full ML pipeline, heavy infrastructure, research-oriented

---

## Community Consensus

### r/algotrading (2024–2026 consensus)
1. **Most validated retail strategy**: Mean reversion on liquid assets (daily timeframe)
2. **Second most discussed**: Momentum / trend following
3. **Pairs trading**: Popular for statistical arbitrage (bank pairs, mining pairs)
4. **Regime detection**: Highly praised — use mean reversion in choppy markets, trend following in breakouts
5. **RL/ML**: Most hype, hardest to make robust; high overfitting risk
6. **Tools recommended**: VectorBT for research, Backtrader for event-driven, Freqtrade for full bot pipeline

**Sobering community wisdom (NautilusTrader debate, Aug 2025, 11k stars, 682k downloads)**:
- "99.5% options success rate, but 0.5% failures erased everything"
- Multiple traders: "transitioned from trading to long-term investing → wealth increased significantly"
- "To generate $200k/year via trading, need ~$2M capital with disciplined 10% return"
- "Crypto bots execute arbitrage for $0.10 gains — markets are that efficient"
- Goldman alum: "automated trading has heavy regulatory scrutiny; not plug-and-play"
- **Overwhelm consensus**: long-term index fund investing + career income beats active trading for most technically-skilled people

### r/AusFinance (Australian context, 2024–2026)
- Short-term (<3 yrs): HISA / term deposits only — do NOT put short-term capital in shares
- Medium-term: ETF DCA via VAS (ASX) + VGS (global); use Vanguard/Betashares Direct/Pearler
- Short-term trading: consistently, strongly discouraged
- First Home Super Saver Scheme (FHSS): mentioned for first-home buyers as a guaranteed ~15% tax saving
- SMSF: growing discussion but still niche/specialist

### r/AusFinance / r/ausstocks general sentiment
- "Just buy VAS and VGS" is the dominant answer to any investment question
- Active trading gets downvoted; index fund discussion gets upvoted
- ASX speculation: r/ASX_Bets is the venue; everyone else knows it's a meme

---

## Recommended Starter Stack

### For ASX + days-to-months time horizon

**Data**: `yfinance` (free, .AX suffix) → OpenBB for research screening
```python
import yfinance as yf
cba = yf.download("CBA.AX", period="2y", interval="1d")
```

**Backtest strategy**: `backtesting.py` for quick prototype; `backtrader` for multi-instrument
```python
# backtesting.py: ~15 lines to test a strategy on any ASX stock
```

**Portfolio weights**: `PyPortfolioOpt` (Efficient Frontier or HRP)
```python
from pypfopt import EfficientFrontier, risk_models, expected_returns
```

**Evaluate results**: `QuantStats`
```python
import quantstats as qs
qs.reports.html(returns, benchmark="CBA.AX", output="report.html")
```

**Live execution** (if you go there):
- IBKR Australia via `ib_insync` Python library
- Backtrader has native IBKR integration

---

## What Doesn't Work (Community Warning List)

1. **Day trading ASX with <$500k capital**: Transaction costs + spreads kill returns
2. **RL/ML black-box on short time series**: Overfit, don't generalise out-of-sample
3. **Any strategy with <5 years backtest history**: Likely curve-fitted
4. **Newsletter/screener signal chasing**: Adverse selection, priced in before you act
5. **HFT at retail**: Institutional bots execute sub-$0.10 arb; you can't compete
6. **Backtrader's main repo**: Development stalled; use cloudQuant fork or switch to backtesting.py / VectorBT

---

## Curated Resources

### Aggregator / Awesome lists
- `https://github.com/merovinh/best-of-algorithmic-trading` — 110 projects, ~330k total stars, updated weekly
- `https://github.com/wilsonfreitas/awesome-quant` — broad quant finance across languages
- `https://github.com/wangzhe3224/awesome-systematic-trading` — systematic trading focus
- `https://freebacktesting.com/code-based` — comparison table with star counts

### Books (community top picks)
- "Advances in Financial Machine Learning" — Marcos Lopez de Prado (mlfinlab is the code)
- "Quantitative Trading" — Ernest Chan
- "Algorithmic Trading" — Ernest Chan
- "Python for Algorithmic Trading" — Yves Hilpisch
