# The Replied set keys on the Platform's own Comment identifier

A Comment is recorded under the identifier its Platform gives it, and never under a hash of its text.

A text hash changes when the text is edited, so an edited Comment would look like a new one and receive a second Reply. That is the exact failure the Replied set exists to prevent, and a hash fallback would manufacture it. The Platform's own identifier does not have that property.

Which identifier exists is a fact about each Platform rather than a choice: Instagram always exposes the Comment `pk` in its permalink, TikTok always exposes the `cid` inside the Comment node's React props, and Facebook exposes `comment_id` in the timestamp anchor only sometimes.

**Consequences.**

- The Replied set holds Platform-shaped keys, so it is not a uniform table and anything reading it is written per Platform.
- **Identity is not addressability.** Holding a Comment's identifier does not mean the Comment can be found on the page. On TikTok the `cid` cannot locate the element at all, so the write path must re-find the Comment by author and text and then compare the identifier it reads against the one it holds before acting.
- That comparison is worth having on its own, because it is also the Confirmation that a Reply landed against the intended Comment. One mechanism answers both questions, so it is built once and named once.
- **Where no identifier exists, the Comment is skipped and Escalated rather than hashed.** On Facebook this is a real outcome, since the anchor is frequently absent. An unanswered Comment is invisible; a duplicate Reply is public, and a fallback would trade the invisible cost for the visible one.
- Because the key is the durable record, changing its shape later orphans the history behind it. The shape is effectively permanent from the first recorded Reply.
