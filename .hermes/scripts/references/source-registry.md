# News Source Registry
*Last updated: 2026-07-02*

All sources currently integrated into `news_feed_ingest.py`.

## API Sources (require key)

| Source | Endpoint | Key env var | Sections/topics | Full text | Daily limit |
|---|---|---|---|---|---|
| Guardian Open Platform | https://content.guardianapis.com/search | GUARDIAN_API_KEY | world, australia-news, us-news, technology, environment, science, politics | YES (show-fields=body) | 500 req |

## Dedicated RSS / Atom (no key)

| Source | URL | Format | Full text | Topic |
|---|---|---|---|---|
| The Conversation AU | https://theconversation.com/au/articles.atom | Atom | YES | AU current affairs + analysis |
| The Conversation Global | https://theconversation.com/articles.atom | Atom | YES | Global analysis |
| The Diplomat | https://thediplomat.com/feed/ | RSS | Partial | Asia-Pacific geopolitics |
| Politico | https://www.politico.com/rss/politicopicks.xml | RSS | Partial | US politics |
| Foreign Affairs | https://www.foreignaffairs.com/rss.xml | RSS | Partial | Geopolitics + IR |

## Geopolitics Bundle (no key)

| Source | URL | Notes |
|---|---|---|
| Crisis Group | https://www.crisisgroup.org/rss.xml | Conflict + diplomacy |
| UN Peace & Security | https://news.un.org/feed/subscribe/en/news/topic/peace-and-security/feed/rss.xml | UN-level conflict/peacekeeping |
| Bellingcat | https://www.bellingcat.com/feed/ | Open-source investigation, conflict verification |

## Google News Paywalled-Outlet Pass (titles only, no key)

| Source | Google News RSS |
|---|---|
| AFR | https://news.google.com/rss/search?q=site:afr.com&hl=en-AU&gl=AU&ceid=AU:en |
| Bloomberg | https://news.google.com/rss/search?q=site:bloomberg.com&hl=en&gl=US&ceid=US:en |
| The Economist | https://news.google.com/rss/search?q=site:economist.com&hl=en&gl=US&ceid=US:en |
| Reuters | https://news.google.com/rss/search?q=site:reuters.com&hl=en&gl=US&ceid=US:en |

*Note: Full article text not available through this path — titles/URLs only.*

## HackerNews API (no key, stdlib only)

| Endpoint | Description | Filter |
|---|---|---|
| https://hacker-news.firebaseio.com/v0/topstories.json | Top story IDs | Fetches top N; filters score >= 50 |
| https://hacker-news.firebaseio.com/v0/item/{id}.json | Story detail | title, url, score, comments |

*Topic: tech/AI/science. Score >= 50 threshold eliminates low-signal stories.*

## Finance — yfinance (no key, requires pip install --user yfinance)

| Tickers | Source | Data |
|---|---|---|
| SPY, EWA, GLD, BTC-USD, NVDA | Yahoo Finance (via yfinance) | Latest price, % change vs prev close, news headlines + summaries |

*Tickers configurable via FINANCE_TICKERS env var (comma-separated).*

## Removed / Excluded

| Source | Reason |
|---|---|
| ACLED RSS | Malformed XML (invalid token at byte 195) |
| Chatham House RSS | 403 Forbidden |
| GDELT Doc API v2 | Rate-limited (1 req/5s), returns empty body in practice |
| archive.ph | Legally toxic (FBI subpoena Oct 2025) |
| 12ft.io / Google Cache | Paywall bypass — prohibited |
