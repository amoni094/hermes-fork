# Hermes tool mapping for Superpowers

Core mappings used by this port:

- clarify requirements -> `clarify`
- inspect code/files -> `read_file`, `search_files`
- implement changes -> `patch`, `write_file`, `terminal`
- execute tests/builds -> `terminal`
- manage task checklist -> `todo`
- delegate focused workers -> `delegate_task`
- validate current config/state -> Hermes-native list/status commands or direct file readback
- create or patch skills -> `skill_manage`, `skill_view`

Important Hermes-specific differences from upstream:

- Some upstream Superpowers skills already exist here as first-class Hermes skills and should be reused instead of duplicated.
- `delegate_task` is asynchronous; never claim delegated success without independent verification.
- Hermes can enforce lighter-weight plans and todo tracking directly, so the port favors concise execution artifacts over framework ceremony.
