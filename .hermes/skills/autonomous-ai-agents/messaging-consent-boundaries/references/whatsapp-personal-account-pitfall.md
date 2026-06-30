# WhatsApp personal-account pitfall

Session lesson:
- When Hermes is paired to WhatsApp through the QR bridge on a personal account, the connection should be treated as access to the user's live WhatsApp account, not as an isolated test bot.
- A successful pair/restart can make Hermes able to see or act within existing chats on that account.

Operational takeaway:
- Do not use any existing chat as a test target without express consent.
- If the user wants a 'separate bot number', recommend a dedicated number/account or WhatsApp Cloud/business setup rather than attaching Hermes to the personal account.
- If the user objects after pairing, the safest next action is to disable the current integration until isolation is in place.

Preferred phrasing after a breach:
- apologize directly
- confirm 'I will not contact any of your contacts without your express consent'
- offer to disable the integration now
