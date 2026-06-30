---
name: messaging-consent-boundaries
description: Prevent accidental contact with the user's real-world contacts when configuring or troubleshooting Hermes messaging platforms.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [messaging, whatsapp, consent, privacy, safety, gateway]
---

# Messaging Consent Boundaries

Use this skill whenever working on Hermes messaging platforms that connect to a user's real account, contact list, inbox, or live chat graph — especially WhatsApp, Telegram, Signal, Discord DMs, Slack, email, SMS, or multi-platform gateway setup.

## Core rule

Do not enter, open, reply in, test against, or otherwise interact with any real user conversation unless the user gives express consent for that specific chat or recipient.

When the account is a personal account rather than a dedicated bot-only account, default to a stricter posture:
- assume the connected account exposes real contacts and existing threads
- avoid any action that could send, trigger, post, or auto-reply
- prefer status inspection, config inspection, logs, and local verification over live chat testing

## Trigger conditions

Load this skill when:
1. pairing Hermes to a messaging platform
2. restarting or troubleshooting the Hermes gateway for messaging
3. enabling a platform adapter on a personal account
4. discussing test messages, pairing validation, or 'just send one to check'
5. the user mentions contacts, private chats, personal numbers, or a desire for a separate bot number

## Safe workflow

1. Establish account type first.
   - Ask yourself whether Hermes is being attached to a personal account, a shared workspace account, or a dedicated bot/business account.
   - If it is personal or unclear, assume personal.

2. Prefer non-contact verification first.
   - Check service status, logs, config, session files, and adapter health.
   - Verify pairing/session establishment without sending messages when possible.

3. Treat live-chat testing as opt-in only.
   - Do not message a contact, reopen an existing thread, or test in a real chat unless the user explicitly authorizes that exact destination.
   - 'Set up WhatsApp' or 'see if it works' is not enough authorization to contact a real person.

4. Recommend isolation when appropriate.
   - For personal messaging accounts, suggest a separate number/account for Hermes if the user wants automation without exposing personal chats.
   - If the user objects to contact access, recommend disabling the current bridge until a dedicated account exists.

5. Distinguish consent from capability.
   - If the user explicitly names an exact recipient or chat destination in the current turn, that satisfies the consent boundary for that destination.
   - Do not keep re-asking for permission once exact-recipient authorization is already present.
   - Authorization alone does not mean delivery happened: only claim a message was sent if a real outbound tool or bridge actually sent it successfully.
   - If no outbound channel is configured in the current environment, say so directly and provide a send-ready draft instead.

6. Honor established email workflow preferences.
   - When the user has established a preferred mail client and send mode for direct email requests, treat that as part of the task workflow, not just a profile note.
   - If the user says 'email this to X' and has established 'send automatically unless I say draft it', default to the send path rather than offering a draft.
   - Use the user's preferred sign-off name in the composed message.
   - Still verify capability before claiming delivery: if the preferred mail client can only open a compose window from automation, say that plainly and avoid falsely claiming the email was sent.

7. If accidental contact may have occurred, respond clearly.
   - Acknowledge the issue directly.
   - Confirm the new boundary in explicit terms.
   - Offer the safest immediate mitigation, usually disabling the active integration.

## Platform-specific pitfall: WhatsApp QR pairing

Pairing Hermes to WhatsApp via QR usually attaches Hermes to the full WhatsApp account behind that number, not to an isolated sandbox. Once the bridge is connected, Hermes may have visibility into existing chats and contacts on that account. Therefore:
- do not assume pairing is harmless
- do not use existing chats as a test surface without express consent
- prefer a dedicated number/account for Hermes if separation matters

## Response pattern after a user correction

When the user says some form of 'do not talk to my contacts without my express consent', reply with all of the following:
1. a direct apology
2. an explicit confirmation of the boundary
3. a concrete operational rule ('no sending, no entering chats, no replying without express consent')
4. an offer to disable or isolate the integration

## Pitfalls

- Treating 'pair the account' as permission to use real chats
- Using an existing contact thread as the easiest test target
- Failing to distinguish a dedicated bot number from a personal account
- Explaining the system before acknowledging the user's boundary breach

## Reference

See `references/whatsapp-personal-account-pitfall.md` for the session-specific lesson that motivated this skill.
See `references/email-recipient-authorization-and-tooling.md` for the distinction between exact-recipient consent and actual outbound delivery capability.
See `references/thunderbird-email-workflow-preference.md` for user-level email workflow defaults around Thunderbird, automatic sending, and preferred sign-off handling.

## Success criteria

- Messaging setup/troubleshooting is completed without contacting real people unless explicitly authorized
- The user is warned when a personal account exposes real chats
- Testing uses non-contact evidence first, and dedicated bot accounts when available
