---
name: email-compose-and-send
provides: [email_send]
triggers:
  - user asks to send, write, compose, or draft an email
  - user says 'email X about Y' or 'send a message to X'
  - sending or opening a compose window via Thunderbird on this Linux Flatpak system
  - user wants to auto-send or save a draft via the desktop email client
description: Use when composing and sending email via Thunderbird on the user's desktop. Covers draft workflow, recipient resolution, Flatpak launch, and send-vs-draft decision.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [email, thunderbird, flatpak, compose, send]
    related_skills: [messaging-consent-boundaries, computer-use]
related_skills:
  - autonomous-agent-loop-design
  - verification-before-completion
  - messaging-consent-boundaries
  - computer-use
---

# Email Compose and Send

## Overview

Covers the full lifecycle of drafting and sending email from Hermes: resolving the recipient, composing the body, and dispatching via Thunderbird (Flatpak install on this system). The default is auto-send unless the user asks for a draft review.

User signs off as **Alexey**. Never prompt for a sign-off name.

## Recipient Resolution — Do This First

Before drafting, check memory/user profile for the recipient's address. Only ask the user if it is genuinely absent from:
- Current user profile memory
- Earlier in the current session (scroll back first)

Never ask for an address that was provided earlier in the session, even across context compaction.

## Compose Workflow

1. Draft the full email in chat (subject + body) for user review.
2. On "send as is" — send immediately, no further confirmation needed.
3. On "draft" or "review first" — open Thunderbird compose window for user to send manually.

Default: **auto-send** unless the user explicitly requests a draft.

## Thunderbird on This System

Thunderbird is installed as a **Flatpak** (not in PATH).

```
Package ID:  net.thunderbird.Thunderbird
Launch via:  flatpak run net.thunderbird.Thunderbird
```

Do NOT try `thunderbird` as a bare command — it will return exit 127.

### Sending Options (in preference order)

**Option 1 — computer_use UI automation (most reliable for full body)**

Use `computer_use` to drive the Thunderbird compose window directly:
1. Launch: `flatpak run net.thunderbird.Thunderbird`
2. Wait for window to load (~5s), capture with `computer_use(action='capture', mode='som')`
3. Click Write/Compose button
4. Fill To, Subject, Body fields via `computer_use(action='type', ...)`
5. Click Send

This is the preferred method when the body is long or contains special characters.

**Option 2 — `-compose` flag (only for short, simple bodies)**

```bash
flatpak run net.thunderbird.Thunderbird \
  -compose "to='addr@domain',subject='...',body='...'"
```

Limitations:
- Body URL-encoding is unreliable for long content with quotes, ampersands, or dollar signs
- Body may be silently truncated or malformed
- Do NOT use for emails over ~200 words

**Option 3 — mailto: URI via xdg-open**

```bash
xdg-open "mailto:addr@domain?subject=...&body=..."
```

Same limitations as option 2. Use only as last resort.

## Common Pitfalls

1. **Calling `thunderbird` bare** — exits 127 on this system. Always use `flatpak run net.thunderbird.Thunderbird`.
2. **Using `-compose` for long bodies** — special characters (quotes, `$`, `&`) corrupt or truncate the body silently. Switch to `computer_use` UI automation for anything non-trivial.
3. **Asking for an address the user already provided** — check session context and memory first. Asking again wastes a round-trip and signals you weren't paying attention.
4. **Asking for send confirmation after "send as is"** — that phrase is an unconditional send instruction; don't ask again.
5. **Forgetting the sign-off** — always sign as **Alexey** unless the user says otherwise.

## Verification

After send attempt via computer_use:
- Capture the Thunderbird window and confirm the compose window closed or shows a "Message Sent" indicator
- If it failed, check the Drafts or Outbox folder visually

## Reference

Session context: Thunderbird Flatpak discovery and `-compose` body-encoding failure documented 2026-07-04.
