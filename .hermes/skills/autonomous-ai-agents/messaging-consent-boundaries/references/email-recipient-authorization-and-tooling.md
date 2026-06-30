# Email recipient authorization and tooling fallback

Session lesson:
- The user explicitly authorized a specific real-world email recipient and asked the agent to send prior analysis.
- Consent was present for that exact destination, so the privacy boundary was satisfied.
- However, the active CLI session had no configured outbound email tool or messaging bridge capable of actually sending mail.

Operational takeaway:
- Separate permission from capability.
- Exact-recipient authorization allows contact in principle, but do not imply delivery unless a real outbound tool is available and used successfully.
- When capability is missing, state the limitation plainly and provide a ready-to-send subject/body draft the user can paste into email.

Recommended response shape:
1. Acknowledge the request.
2. State whether actual sending is possible in this environment.
3. If not possible, provide a polished send-ready draft addressed to the authorized recipient.
4. Avoid asking for repeated consent when the user already named the exact recipient in the current turn.
