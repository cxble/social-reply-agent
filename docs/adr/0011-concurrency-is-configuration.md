# Concurrency is configuration; the safety controls are not per-worker

The number of browser workers is deployment configuration, defaulting to one. The Daily cap, the Kill switch, the Replied set and each Platform's write permission are shared state rather than worker-local state, and a global concurrency limit is enforced so that no Platform agent can start a worker beyond the configured allowance.

With one worker the distinction is invisible, which is exactly why it is decided now. Every one of those controls fails silently once it becomes per-worker: two workers with their own daily counters post twice the cap, two Replied sets reply to the same Comment, two Kill switches each stay on. None of those failures announces itself — they show up as an Account that is suddenly behaving twice as fast as it was configured to.

The alternative, a lock held around every write, buys the same correctness at the cost of the throughput the workers were added for. So the split is between state and work: the counters and the record are owned outside the workers, and only the work is parallel.

**Consequences.**

- The cap counter, the Replied set, the Kill switch and write permission live where every worker reads them. A worker that cannot reach them posts nothing — shared state being unavailable is a stop, not a degrade.
- Raising the worker count is an explicit configuration change requiring memory, session-isolation and write-coordination testing first. It never happens automatically, and never because a Backlog is large.
- Nothing here is built yet, so the pass loop must be written from the start to take the worker count as an input and to read its controls from shared state. A one-worker design retrofitted to many is a rewrite; a count-aware design deployed with one worker is not.
- One worker on the current machine is therefore a deployment fact, not a property of the architecture. The machine's ceiling is documented as hardware, so that a later second machine is procured rather than mistaken for a software limit.
