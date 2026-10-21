# Browser automation instead of platform APIs

Every Platform is driven through a logged-in browser session, not its official API.

The APIs were the obvious route and were rejected on purpose. This is a personal tool for the user's own Accounts, answering Comments on their own Posts, and the official APIs either do not expose comment replies at all or gate them behind app review, business verification, and rate limits that would block an unattended personal tool. Policy is the real constraint: several Platforms' terms explicitly forbid scripting the site, so an API-first design would have traded a technical problem for a contractual one.

**Consequences.**

- The Session is the credential. There is no token to rotate, so losing the Session looks exactly like the agent being broken, and it fails quietly.
- Every read and every write is a DOM interaction, so Selector rot is the primary failure mode rather than a secondary risk.
- No Platform can be treated as a stable interface. Everything is expected to break, which is why every Adapter starts in a dry run.
