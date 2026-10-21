# A dead Session stops the agent, and the agent never re-logs-in

When a Comment pass finds the Session logged out or challenge-walled, the Platform agent stops, posts nothing, and leaves a marker for the user. It does not try to authenticate again.

Letting the agent log back in is the behaviour that most reliably turns a soft challenge into a hard checkpoint. A challenge page is the Platform asking whether a human is present, and an unattended process answering it correctly on the first attempt, at an hour no human would be awake, is precisely the answer it is looking for. Stopping costs a missed Comment pass. Re-logging-in wrongly costs the Account.

**Consequences.**

- Losing a Session is a human task, so the marker has to carry which Account died and when, because nothing else will.
- The user's login and the agent's use of it are strictly separate acts: `login.py` produces a Session, and the agent only ever consumes one. It never refreshes or repairs one.
- A Platform can therefore sit idle for a long time with nothing wrong inside the agent. The agent has no way to notice staleness by itself, so silence is not evidence of health.
