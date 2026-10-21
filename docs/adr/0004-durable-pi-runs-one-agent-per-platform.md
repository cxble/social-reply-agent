# durable-pi runs one agent per Platform

The agents are durable-pi agents, one per Platform, rather than a single script driving all of them.

An unattended agent that must never answer the same Comment twice has exactly one piece of state that has to survive a crash mid-reply, and durable-pi's checkpoints are built for that. One agent per Platform was chosen over one agent for everything because the Platforms differ enough that a failure on one should not stop the others, and because each Adapter then owns its own state and its own pacing.

**Consequences.**

- The Replied set must be durable in the same way, or the guarantee is only as good as the last checkpoint.
- The runtime inherits durable-pi's dependency on the `dpi-backend` service and its model routing, including the OpenRouter credential.
