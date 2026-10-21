# TikTok is read in a headed browser, and an empty Comment list is a failure

TikTok serves a logged-out **headless** Chromium the comment panel with every row left as a
grey skeleton placeholder. The container, the counters and the composer all render; not one
Comment does. The same page in a **headed** browser, equally logged out, returns the Comments.

Measured on `@benooicb`, 2026-10-21. Headless: `comment_nodes: 0` on a Post reporting hundreds
of Comments. Headed, unauthenticated: 40 nodes, 40 non-empty bodies, twice, before and after
scrolling.

**There is a second, independent way to get the same zero, found the same day.** The comment
panel has two tabs — `Comments` and `You may like` — and it **opens on `You may like`**. That
tab's tiles are skeletons too, so `[class*="DivCommentItem"]` matches nothing there either. A
headed harvest of twelve Posts returned zero Comments on every one of them for exactly this
reason: nothing was blocked, no CAPTCHA was shown, and the correct count (`Comments 124`) was
rendered on the page the whole time, unread, beside the wrong tab.

So a zero from this Platform has at least two unrelated causes, and they are indistinguishable
from the output alone. Neither raises anything.

Two facts were tangled in that zero and both are worth separating.

The first is the mode. A headless read is not a restricted read — it is a **silently empty**
one. Nothing throws, no page error fires, the Session is alive, and the Comment list comes back
as an empty list rather than as a failure. The Platform agent finds nothing eligible, reports a
clean pass, and the Daily cap never fills because there is never anything to reply to. There is
no signal in the output that distinguishes this from a genuinely quiet comment section.

The second is the selector. The probe that produced the zero asked for
`[data-e2e^="comment-level"]`, which matches **no node at all** on the living DOM, headed or
headless. It came from `comment-identity.md`, a document written from other people's captured
HTML without a live page. So a selector that never matches was queried in a mode that returns
nothing to match, and the two faults produced one indistinguishable `0`.

**Decision: the read path runs headed, and an empty Comment list is an outcome the Adapter must
be able to distinguish from a quiet comment section.**

Concretely: a Post whose own page reports a non-zero `commentCount` but from which zero
Comments were read is a **failed read**, not an empty one. That count is on the same page that
withheld the Comments, so the check costs nothing and is available even logged out.

**Consequences.**

- This partly reverses ADR 0003's container reasoning. That ADR accepted detection risk from a
  container on the grounds that "no GPU, headless by default" was a cost the dry run and the
  Daily cap would absorb. It is not a cost to absorb; on this Platform it is a total read
  failure that reports success. The browser may still be a separate movable process, but it
  cannot be a headless one, so the host it moves to needs a display.
- An empty Comment list is now a failure the code must be written to detect. A pass that reads
  zero Comments from every Post is the failure mode, and it is invisible to every other control
  in the system: the Kill switch never trips, the Session never dies, the Replied set never
  grows. Nothing but an explicit count check catches it.
- **Selecting the Comments tab is part of the read, not setup.** A read path that assumes the
  panel opens on Comments is wrong on this Platform by default, and wrong in the silent way.
  The Adapter must select the tab and then verify against the count before it believes an empty
  list.
- Two traps that both yield an empty list means the empty list itself carries no information.
  The count check is therefore not a nicety layered on top of the read — it *is* the read's
  only evidence that it happened at all.
- The count check makes a Platform-side change to the Comment selector loud. If
  `[class*="DivCommentItem"]` stops matching, the read returns zero against a non-zero count and
  the Adapter reports a failed read rather than a quiet day. This is the property that
  `comment-identity.md`'s third consequence asked for — selectors that rot should rot visibly.
- **The headed requirement is unmeasured on Facebook and Instagram.** It is established for
  TikTok only, and it is not safe to generalise from one Platform to three. Until it is
  measured, each Adapter owns the question for its own Platform.
- A headless read is still correct for work that does not read Comments. The distinction is
  about the read path, not about every browser the system starts.
- This is the fourth time in this project that an absence has been read as a fact. The others
  were a missing listing entry, a missing reply, and a retracted true claim. The pattern is
  consistent enough to name: **a zero needs a positive control before it means anything.** Here
  the positive control was the Comment count on the same page, and it was available the whole
  time.
