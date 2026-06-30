# Google News RSS fallback for recent briefings

Use this when a specialized recent-news skill is installed but active coverage is incomplete.

## Why this fallback exists
A research skill can be correctly installed yet still lack enough active sources to support a broad current-events briefing. Common gaps include:
- no general web backend
- no X/Twitter auth
- no YouTube/transcript backend
- no planner/provider key, causing deterministic fallback only

In that situation, use a lightweight live-news feed to widen coverage instead of pretending the skill is comprehensive.

## Recommended pattern
1. Keep the specialized skill in the loop.
   - verify install/listing
   - run diagnostics if available
   - run at least one sample query to confirm output shape

2. Build one query per user topic.
   - Avoid a single giant query.
   - Include the time window term such as `when:30d`.
   - Use geography-sensitive editions when relevant, e.g.:
     - Australia: `hl=en-AU gl=AU ceid=AU:en`
     - United States: `hl=en-US gl=US ceid=US:en`

3. Extract structured fields only.
   - date
   - title
   - outlet/source
   - link
   - optional days_ago

4. Synthesize themes from several items per topic.
   - Lead with the dominant development.
   - Mention only the clearest supporting examples.
   - Flag thin coverage when the topic results are weak or noisy.

## Example topic buckets that worked well
- Australian politics / major Australian news
- US politics / major US news
- finance / economics
- Middle East geopolitics
- Oceania / Pacific geopolitics
- Ukraine war
- rock / metal music
- manual / non-EV enthusiast cars
- tech / AI

## Phrasing discipline
Use language like:
- "The skill is implemented and working, but source-limited in this environment."
- "I supplemented it with live Google News RSS searches for the last 30 days."
- "This is a skill + equivalent live-news workflow, not pure skill output."

Avoid language like:
- "The skill covers everything we need" when diagnostics show missing sources.
- "These are all the major developments" when coverage is obviously partial.

## Durable lesson from this session
For broad 30-day briefings, installation verification and coverage verification are separate steps. If the skill’s active sources are narrow, supplement with a current low-friction news feed and state that clearly in the answer.
