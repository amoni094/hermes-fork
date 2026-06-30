# External source stack evaluation

Use this note when a user asks whether a new retrieval layer will improve news, recommendations, or media lookup.

## Core comparison frame
Evaluate four things separately:
1. current-stack gaps
2. new-stack source reach
3. auth/setup burden
4. whether the gain is discussion-layer or structured-data-layer

Do not collapse these into a single "better/worse" judgment.

## Good evaluation sequence
1. Inspect the current agent stack first.
   - verify current search works
   - verify current extraction works
   - inspect config for backend routing
2. Identify the real bottleneck.
   - Example: search may work while extraction is misconfigured.
3. Read the proposed tool's docs/source for:
   - install path
   - dry-run/status commands
   - auth requirements
   - side effects in "doctor"/"setup" style commands
4. Run a reversible trial.
   - isolated venv preferred
   - use dry-run first
   - prefer machine-readable status output when it avoids side effects
5. Report by use case, not by feature count.
   - news/current-events
   - recommendations/discussion lookup
   - canonical metadata lookup

## Durable lessons from Agent Reach evaluation
- A source-expansion tool can be genuinely useful without replacing the main agent stack.
- For news/research, community and platform-native sources can be a meaningful upgrade even if general web search is already decent.
- For music/movie tasks, discussion and recommendation coverage is different from canonical metadata coverage. Reddit/YouTube/social sources help with taste and buzz; they do not automatically replace TMDb/Letterboxd/MusicBrainz/Spotify-style data.
- Fixing the current stack may yield a faster win than adding a new one.

## Concrete verification pattern used
- Verified current Hermes `web_search` in a fresh one-shot chat.
- Verified current Hermes `web_extract` failure path in a fresh one-shot chat.
- Read live config to confirm backend routing.
- Installed the candidate tool only in an isolated `/tmp` venv.
- Used `install --dry-run` and JSON status output for the trial.

## Specific pitfall captured
If a tool offers a human-friendly `doctor` command, inspect whether it also writes skills/config automatically. During evaluation, prefer a no-side-effect variant if one exists.

Example from this session:
- Hermes current stack had working SearXNG search.
- Hermes current stack had broken extraction because `web_extract` was effectively routed to a search-only backend.
- Agent Reach provided broader social/community source pathways, but required optional installs/auth for most of the high-value channels.

## Recommended output shape
- short verdict
- strongest gains
- weak/no-gain areas
- immediate fix in current stack
- whether the new stack should be primary or sidecar
