# A discovered Post stays tracked after it leaves the discovery window

A Comment pass notices a Post for the first time only while the Post is inside the Discovery window. Once noticed, the Post is tracked, and it stays tracked after it ages out, so Comments arriving on it later are still seen.

ADR 0008 recorded the opposite as an accepted hole: "A Comment arriving after activation on a Post that later falls out of the scan window is never seen." The hole is real, and it is paid by exactly the Posts most worth watching — the ones that drew traffic while they were new keep drawing it.

Discovering and tracking are two different decisions that happened to share one boundary. The Discovery window decides what may be *newly noticed*; tracking decides what remains *watched*. Collapsing them means choosing between a pass that grows without bound as every Post ever published stays in scope, and a hole in the middle of the Posts that matter. Splitting them costs neither.

**Consequences.**

- A Tracked post is a record with a life of its own: noticed, then tracked, then closed. It is not re-derived from the Post's age on each pass, because the page does not carry a Post's age reliably and a derived record cannot distinguish "aged out" from "never seen".
- ADR 0008's hole survives for Posts never noticed while young, and only for those. Re-tracking an aged Post is not re-noticing it.
- Tracking ends when the Post's eligible Backlog is resolved or the Post is explicitly closed. The retention rule is configuration.
- An aged Post may be deleted, restricted, or otherwise stop loading. That is not a Session failure: it closes the Tracked post, and it must not stop the Platform agent.
- Seeding still runs once and still uses the Baseline boundary from ADR 0008. Tracking changes what happens after activation, not what counts as a Baseline Comment.
