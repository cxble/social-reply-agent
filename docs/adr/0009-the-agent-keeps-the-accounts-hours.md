# The agent keeps the Account's hours

A Platform agent starts work only inside an Active window — roughly 08:00–23:00 local, with the day's start jittered by up to ±45 minutes. Nothing new begins outside it.

At volume the temptation is to treat the Daily cap as the only limit and run the machine around the clock, because the cap is the thing that protects the Account. It is not. An Account that answers Comments at 04:00 every night, at a steady cadence, is producing a pattern no person produces, and the schedule is a signal in its own right — independent of how many Replies were sent or how slowly. Running out the clock to reach a number spends the Account to buy throughput.

The window also bounds what the cap can mean. Throughput is not "as many as the cap allows"; it is "as many as Pacing allows inside the window". The cap is a backstop against a misconfigured or misbehaving Pacing, not a quota to work through.

**Consequences.**

- The Daily cap resets on the local calendar day and survives restarts, so neither a restart nor a clock change buys Replies.
- A pass caught by the window closing stops starting new work and checkpoints. It does not finish the queue.
- Comments arriving outside the window are not lost. The next window's Comment pass discovers them and they join the Backlog, so coverage comes from scanning rather than from staying awake.
- The window and the jitter are configuration, and the jitter is operational: it keeps the day from beginning on a machine-regular edge. It is not the control that keeps the Account unflagged — Pacing is.
- Operating hours are per Platform and read in the Account's local timezone, so a Platform agent is never woken by a server clock in another region.
- The Daily cap, the Active window and Pacing are configuration rather than constants. That has a cost worth naming: a limit the deployment can raise is a weaker guarantee than one welded into the code, and the 10-per-day figure this replaces was only ever a default that read as a decision. Configurability is accepted anyway, because the machine's ceiling and the deployment's ceiling are different things, and a safety limit that cannot move with them is one that gets edited in a hurry.
