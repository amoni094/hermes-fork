# Thunderbird email workflow preference

## Workflow defaults

- When the user says "email this to <recipient>", use Thunderbird, sign as **Alexey**, and send automatically unless they ask for a draft.
- "Send as is" is an unconditional send instruction — do not re-confirm.
- Compose with full subject + body in chat first for the user to review, then send on approval.

## Recipient resolution

- Check current session context and memory/user profile before asking.
- Asking for an address already provided earlier in the session (even across context compaction) is an error — scroll back first.

## Thunderbird install on this system

Thunderbird is installed as a **Flatpak**, not in PATH. Bare `thunderbird` returns exit 127.

```
Package ID:  net.thunderbird.Thunderbird
Flatpak run: flatpak run net.thunderbird.Thunderbird
```

## Send methods (preference order)

1. **computer_use UI automation** — most reliable, handles any body length and special characters.
   Launch Thunderbird, capture with `mode='som'`, click Compose, fill fields, click Send.

2. **`-compose` flag** — only for short/simple bodies (~200 words max).
   ```
   flatpak run net.thunderbird.Thunderbird -compose "to='...',subject='...',body='...'"
   ```
   Fails silently on long bodies or special characters (`$`, `&`, single quotes).

3. **`xdg-open mailto:` URI** — last resort; same limitations as option 2.

## Capability honesty

Only claim "sent" after a real outbound send path succeeds.
If automation only opens a compose window, say that plainly. Never claim delivery without evidence.

## Session history

- 2026-07-04: Discovered Thunderbird is Flatpak-only. `-compose` flag unreliable for long email bodies. Correct fallback is `computer_use` UI automation.
