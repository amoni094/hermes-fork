# Search fallback implementation notes

## Files touched in a representative implementation
- `tools/web_tools.py`
  - add configurable search fallback parsing
  - build ordered provider candidate list
  - keep provider availability checks non-fatal
  - aggregate bounded provider failure text
- `hermes_cli/config.py`
  - add `web.search_fallback_backends` to defaults
- `tests/tools/test_web_tools_config.py`
  - success via fallback
  - combined error when configured providers all fail
  - configured fallback order outranks default order
- `website/docs/user-guide/configuration.md`
  - document backend list and `search_fallback_backends`

## Useful test pattern
For ordering assertions, avoid real provider gating. Use fake providers and monkeypatch:
- `agent.web_search_registry.get_provider`
- `agent.web_search_registry.list_providers`

This isolates dispatch ordering from env-var availability logic.

## Config-shape pitfall
After `hermes config set web.search_fallback_backends '...[...]'`, verify the file content is a real YAML list if the code expects a list. A CLI success message alone is not enough. If the value lands as a quoted string, either:
- normalize the YAML to a list, or
- make the parser robust to the accepted string form and verify that behavior with tests.

## Verification commands
```bash
python -m pytest -q -o addopts='' tests/tools/test_web_tools_config.py::TestWebSearchFallbackChain
python -m pytest -q -o addopts='' tests/tools/test_web_tools_config.py -k 'TestWebSearchFallbackChain or exception_in_provider_search_is_sanitized'
```
