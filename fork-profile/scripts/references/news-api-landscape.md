# News API Landscape
*Last updated: 2026-07-02*

## Priority Stack (integrated into news_feed_ingest.py)

| Priority | Source/API | Type | Free Tier | Full Text | Key? | Status |
|---|---|---|---|---|---|---|
| #1 | Guardian Open Platform | REST API | 500 req/day | YES | YES | Active — key in .env |
| #2 | The Conversation (AU + Global) | Atom RSS | Unlimited | YES | None | Active |
| #3 | HackerNews API | REST JSON | Unlimited | Partial (text posts) | None | Active |
| #4 | yfinance (Yahoo Finance) | Python lib | Unlimited | Summaries + price | None | Active (pip install --user yfinance) |
| #5 | Geopolitics RSS bundle | RSS | Unlimited | Partial | None | Active (Crisis Group, UN, Bellingcat) |
| #6 | Politico / Diplomat / Foreign Affairs | RSS | Unlimited | Partial | None | Active (occasional timeout) |
| #7 | Google News paywalled-outlet pass | RSS | Unlimited | Titles only | None | Active (AFR, Bloomberg, Economist, Reuters) |
| skip | Currents API | REST API | 600 req/day | Summaries | YES (free, no CC) | Not integrated — low value vs cost |
| skip | GDELT Doc API v2 | REST JSON | Unlimited* | Metadata only | None | Dead — rate-limited (1 req/5s), returns empty |
| skip | Mediastack | REST API | 100 req/month | No | YES | Too low quota |
| skip | NewsAPI.org | REST API | 24h delay | No | YES | Delay makes it useless for daily briefing |
| skip | ACLED RSS | RSS | Unlimited | Partial | None | Malformed XML |
| skip | Chatham House RSS | RSS | — | — | None | 403 Forbidden |
| paid | NewsAPI.ai / AYLIEN | REST API | Trial only | YES | YES | $249+/mo |
| paid | Bloomberg API | REST API | No free tier | YES | YES | Enterprise only |
| paid | AFR full text | — | No | YES | — | Paywall, no legitimate free path |

## APIs Evaluated but Not Integrated

| API | URL | Notes |
|---|---|---|
| World News API | https://worldnewsapi.com | 10k req/month free, needs key — skip (key not in hand) |
| NYT Article Search | https://developer.nytimes.com | Free with key — possible future addition |
| Open Exchange Rates | https://openexchangerates.org | 1000 req/month free — finance supplement |
| Alpha Vantage | https://www.alphavantage.co | 25 req/day free — too low for regular pulls |
| Marketaux | https://marketaux.com | News + sentiment, 100 req/day free — possible addition |

## RSS Aggregators (self-hosted, evaluated but not deployed)

| Tool | Stars | Notes |
|---|---|---|
| FreshRSS | 15.4k | PHP, Docker-ready, Google Reader + native REST API — high value if deployed |
| Miniflux v2 | 9.4k | Go, lightweight, full REST API — best option if hosting an aggregator |
| tt-rss | — | PHP, older, has API — more complex than Miniflux |
| Feedbin | — | Ruby, hosted SaaS or self-host — paid-first |

*Note: Self-hosted aggregator would centralize all RSS polling and expose a single REST endpoint to news_feed_ingest.py.*

## Finance/Market Data (evaluated)

| Tool | Type | Key? | Notes |
|---|---|---|---|
| yfinance | Python lib | No | Integrated — Yahoo Finance prices + news, no official API |
| OpenBB | Python SDK + FastAPI | No | Macro data, earnings, Fed data — too heavy for ingest script |
| Alpha Vantage | REST API | YES | 25 req/day free — too low |
| Open Exchange Rates | REST API | YES | FX rates only |
