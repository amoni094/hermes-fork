# Public social post summaries without login

Use this when a dashboard needs "top social posts" rather than generic profile links, and the user does not want login-gated platforms in the UX.

## Working pattern from the policy dashboard session

### Goal
Show top 5 recent politician social posts with direct links and short summaries, ordered by engagement in the last week, without asking the user to log in.

### Observed platform reality
- Logged-out Instagram profile and post pages can return HTML, but the useful recent-post surface is effectively login-walled for practical extraction in this workflow.
- Logged-out Facebook profile pages often canonicalize to a login page, so they are poor primary sources for post summaries here.
- Logged-out X profile pages can still expose enough embedded post data in the HTML payload to recover:
  - post text (`full_text`)
  - created timestamp (`created_at_ms`)
  - engagement counts (`favorite_count`, `retweet_count`, `reply_count`)
  - stable status URL via the embedded tweet id

### Recommended extraction order
1. Prefer public X profile HTML when available.
2. Filter to posts from the last 7 days.
3. Rank by a transparent engagement heuristic.
4. Emit direct status URLs plus short summaries and counts.
5. Only if no recent post-level data is accessible, fall back to profile/page metadata (`og:title`, `og:description`, `twitter:description`, `<title>`).

### Engagement heuristic used
A simple transparent score worked well:
- engagement = likes + replies + (reposts * 2)

This is not platform-truth engagement, but it is explainable and stable enough for local dashboard ranking.

### X HTML extraction pattern
From logged-out profile HTML:
- post text can be found near `full_text:"..."`
- timestamp can be found near `created_at_ms:<millis>`
- counts can be found near `reply_count:`, `favorite_count:`, `retweet_count:`
- tweet identity can be reconstructed from the base64 token embedded in keys like `client:VHdlZXQ6...`
  - decoded form looks like `Tweet:<tweet_id>`
  - status URL becomes `<canonical_profile>/status/<tweet_id>`

### Guardrails
- Do not claim Instagram-derived recent post summaries when the extraction path only reaches a login wall.
- Do not emit generic filler like "detected during refresh" when the user asked for actual post summaries.
- If you fall back to metadata, be explicit in code/comments that it is a fallback, not a recent-post extractor.
- Sample-check at least one generated profile after refresh to ensure summaries are actually post-level and linked to real status URLs.

### Verification cues
- Generated payload contains `https://x.com/.../status/...` links.
- Summaries include engagement counts.
- Sample posts are dated within the last 7 days according to extracted timestamps.
- The UI does not send the user to a login-wall-only Instagram page when it claims to show recent top posts.
