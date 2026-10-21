# Comments that predate the agent are ineligible for Replies

When a Platform agent is first activated, the Comments already sitting on the scanned Posts form a Baseline. Nothing in the Baseline is replied to, whether or not it carries a Reply.

The tempting shortcut is to treat an unanswered Comment as work waiting to be done: the Account has not replied, so the Comment must be waiting for one. It is not. The Account may have read it and chosen not to answer, answered it somewhere the agent cannot see, or judged it inappropriate to answer. Absence of a Reply is not evidence of an open question, and an agent that reads it that way will spend its Daily cap working through a backlog the user decided to leave alone.

A Reply that is present is strong evidence the Comment is handled. A Reply that is absent is evidence of nothing. Those are facts about different things, and they are stored as different things.

**Consequences.**

- **Baseline membership and Reply status are two fields, never one.** Collapsing them into a single "handled" flag loses the difference between a Comment that existed before activation and a Comment the agent has actually answered, and the loss is silent: the audit stops being able to say why a Comment was skipped.
- **Seeding and Reconciliation read the same pages under different rules.** Seeding runs once, at activation, and establishes the Baseline. Reconciliation runs afterwards and repairs disagreement between what the page shows and what the Replied set records. Sharing the reader is fine. Sharing the rules is not, and neither may call the other.
- The Baseline boundary is what "new Comment" means from then on, so it is recorded rather than derived. Eligibility depends on when a Comment first appeared, and the page does not carry that fact.
- ADR 0007 applies unchanged inside Seeding: a baseline Comment whose identity cannot be verified is skipped and Escalated, not guessed at.
- A Comment arriving after activation on a Post that later falls out of the scan window is never seen. That is a known hole in coverage, accepted in exchange for a bounded pass.
