# Authenticated social signals via Firefox cookies

Use this reference when a briefing should include a separate personalized section derived from the user's own Reddit/X/browser signal.

## Verified local-first pattern

1. Get explicit approval before using account-backed local session data.
2. Prefer read-only local-session reuse over asking for credentials.
3. Distinguish source confidence clearly:
   - signed-in response verified
   - cookies present but signed-in state not proven
   - blocked by bot/security controls
4. Keep personalized output in a separate heading, not mixed into public-news synthesis.
5. Frame it as recommendation-style signal, not consensus news.

## Firefox cookie-store notes

On Fedora Silverblue with Flatpak Firefox, live profiles are typically under:
`~/.var/app/org.mozilla.firefox/config/mozilla/firefox/`

A common cookie path is:
`~/.var/app/org.mozilla.firefox/config/mozilla/firefox/<profile>.default-release/cookies.sqlite`

Do not assume `~/.mozilla/firefox/` on this setup.

## Collector pattern for this workspace

Default personalization side-channel:
`/var/home/rainbow/.hermes/scripts/social_signals.py --limit 5 --json`

Use it as a read-only side-channel for:
- recent followed-account/feed signal from X
- recent subreddit/feed signal from Reddit when available
- recommendation-style bullets under `## Personalised for you`

## Reporting rule

Say exactly which path worked:
- browser automation
- local cookie-backed HTTP probe
- local collector script

If one source is blocked, do not generalize that to the whole workflow; report the fallback that did work.
