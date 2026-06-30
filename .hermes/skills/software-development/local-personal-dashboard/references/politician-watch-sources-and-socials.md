# Politician watch dashboard: source coverage and social-link augmentation

Use this note when an entity-watch dashboard needs broader named outlet coverage plus richer public social links without pretending the feed is universal.

## Source-registry pattern
- Keep one explicit source registry in the refresh script.
- Represent each source with:
  - stable id
  - display label
  - retrieval mode (`direct`, `google-rss`, or equivalent)
  - URL or query
  - optional allowlist patterns for direct-page link extraction
- Prefer direct extraction for stable, mostly server-rendered pages.
- Add a resilient fallback path for brittle sources (JS-heavy sites, intermittent anti-bot, weak article-link structure). Google News RSS search is a good low-friction fallback for outlet coverage verification.

Example requested-outlet set from this session:
- ABC News
- SBS News
- Reuters
- The Guardian
- The Conversation
- The Australian
- Google News
- 7 News
- Nine News

## Artifact-level verification
Do not stop at "the code includes the source." Verify the generated artifact shows the realized source set.

Recommended pattern:
- collect headlines with `sourceLabel`
- derive `monitoredSources = sorted(unique(sourceLabel))`
- write it into the payload under a status/health block such as `sourceHealth.monitoredSources`
- after refresh, assert every requested label appears in that generated field

This catches cases where a source exists in code but produced zero usable items in practice.

## Social-link augmentation pattern
For public-figure profiles, primary sources are often incomplete. Use a layered approach:
1. Load stable structured handles first (for example from Wikidata):
   - website
   - X/Twitter
   - Instagram
   - Facebook
   - YouTube
2. Scrape linked official websites and public profile pages for outbound anchors to:
   - X
   - Instagram
   - Facebook
   - YouTube
   - LinkedIn
   - TikTok
3. Merge only missing fields so structured sources remain the primary authority.

## Normalization rules
Normalize before storing:
- canonicalize `twitter.com` to `x.com`
- strip trailing slash noise where safe
- reject ephemeral/share URLs such as:
  - Facebook share links
  - X intent/share links
  - Instagram post/reel/story links
- prefer durable profile/account URLs over content-item URLs

## UI/use-pattern note
When politician-specific media hits are sparse, social-profile links can be surfaced as clearly-labeled fallback announcement items. This keeps profiles useful without claiming those links are news coverage.

## Verification ideas
After refresh, count populated link fields across the directory, for example:
- `xHref`
- `instagramHref`
- `facebookHref`
- `youtubeHref`
- `linkedinHref`
- `tiktokHref`
- `websiteHref`

Also count how many profiles gained fallback social-linked announcements. This is a quick regression signal when scraper changes silently reduce enrichment.
