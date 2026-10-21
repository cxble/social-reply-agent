# A dead Session stops the agent, and the agent never re-logs-in

When a Comment pass finds the Session logged out or challenge-walled, the Platform agent stops, posts nothing, and leaves a marker for the user. It does not try to authenticate again.

Letting the agent log back in is the behaviour that most reliably turns a soft challenge into a hard checkpoint. A challenge page is the Platform asking whether a human is present, and an unattended process answering it correctly on the first attempt, at an hour no human would be awake, is precisely the answer it is looking for. Stopping costs a missed Comment pass. Re-logging-in wrongly costs the Account.

## The three holes this left

The rule above is about a Session failure that **announces itself** — a login page, a challenge wall.
Three others were left unrecorded when it was written, and all three are the same failure seen from
different places: **the agent cannot tell a Platform that has stopped serving it from a Platform with
nothing to serve.**

**1. A challenge that is not a page state.** "Logged out or challenge-walled" is a fact about a page.
A Platform can also degrade a Session without any page saying so: the Comments request returns fewer
of them, `has_more` arrives at zero early, a page loop stops after two iterations. Nothing looks
wrong and the pass reports a quiet day, which is exactly what a genuinely quiet Post looks like. It
therefore cannot be caught by reading pages for a signal. It is caught by **agreement with `total`**:
a read that cannot reconcile its own count against the Platform's is a **Truncated read**, and a
Truncated read is a dead Session, not a thin corpus. The evidence is already in hand — Post
`7638968441851907336` reported `has_more: 0` at cursor 60 with 50 of 2,712 Comments read. **A pass
that cannot account for its count stops, posts nothing, and leaves a marker**, because a degraded
Session is the state in which continuing to post turns a soft challenge into a hard checkpoint.

**2. A captcha arriving mid-post.** The Reply may have landed before it arrived, or not. The trap is
the retry: a blind retry is how the agent posts the same Reply twice, which is the largest
correctness risk in this project (ADR 0019, bar 4). **The agent never blind-retries an unknown
outcome.** The Reply is recorded as an **Unknown outcome** — neither posted nor not-posted — and the
agent stops. Treating unknown as "not posted" is the same mistake in the other direction, and it is
the one that produces the double Reply: the record is repaired by **Reconciliation** from the page
later, never by trying again now.

**3. Reconciliation must tell "cannot tell" from "no Reply here".** An absent Reply is evidence of
nothing (ADR 0008). So Reconciliation has three verdicts, not two: the record and the page agree the
Reply is present; the record claims a Reply and the page shows none, which is a real disagreement and
is repaired; and **cannot tell** — the Comment was not found, the page did not render, the read was
Truncated. Collapsing the third into the second makes Reconciliation re-post every Reply the agent
has ever made: a mass duplicate, the worst outcome available. **"Cannot tell" is actioned by
nothing.** Reconciliation reports it and changes no record, and the same count-against-`total` check
that detects a Truncated read is what gates it.

**Consequences.**

- **A page-state check is not enough to detect a dead Session, and an Adapter that only looks for a
  login wall will report a healthy Session through a full degradation.** The check that catches it is
  arithmetic: the read's own count against `total`.
- Losing a Session is a human task, so the marker has to carry which Account died and when, because nothing else will.
- The user's login and the agent's use of it are strictly separate acts: `login.py` produces a Session, and the agent only ever consumes one. It never refreshes or repairs one.
- A Platform can therefore sit idle for a long time with nothing wrong inside the agent. The agent has no way to notice staleness by itself, so silence is not evidence of health.
- **The marker carries the evidence, not just the fact.** A Truncated read's counts (what was read
  against `total`), and an Unknown outcome's identifier, are what let the human tell a challenge from
  a throttle from a genuinely small Post. "The Session died" alone does not.
