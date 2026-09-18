# English-only surface audit

Use this when the user wants Hermes itself kept English-only.

Checklist:
1. Runtime config
   - verify `display.language: en`
   - verify any user-facing runtime language settings are not set to non-English values

2. Backend i18n layer
   - inspect the backend language resolver / supported-language list
   - if the goal is strict English-only behavior, constrain the supported set to English and verify the module still compiles

3. Frontend/docs locale config
   - inspect the website/app locale configuration
   - set the default locale to English
   - reduce configured locales/search languages to English only

4. Localized content trees
   - remove or archive non-English locale catalogs and generated localized docs when the user explicitly wants English-only surfaces
   - verify the removed locale files are actually gone

5. Live-process rollout
   - restart long-lived Hermes siblings such as dashboard and gateway after backend/frontend locale changes
   - verify new PIDs, listeners, and healthy startup
   - call out separately when the current CLI/chat process is still an old live session and needs its own manual restart

6. Response hygiene
   - if repo searches encounter non-English files during the audit, summarize that fact in English rather than pasting those contents unless the exact text is required as evidence

Common pitfall:
- changing repo files only, then forgetting that already-running Hermes processes still serve old in-memory code and old locale state.
