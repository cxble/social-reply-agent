# A Comment nothing covers gets no Reply, and silence is not an Escalation

The reply pipeline has four outcomes, not three: a Canned reply, an Escalation, a Tail Comment, and
**nothing at all**. The fourth was implied everywhere and written down nowhere, and
`docs/labelled-set-tiktok.md` measured it at **61.1% of rows** — the largest class in the corpus
by a factor of three over the next one.

Three of the four are settled. ADR 0002 makes the Canned reply a selection. ADR 0014 and ADR 0016
make Escalation an outcome with its own threshold and its own cost. The Tail is the gap the table
is expected to grow into. What was missing is the decision that **most of a comment section is
meant to go unanswered**, and that answering it is a defect rather than diligence.

This is not a stylistic preference. It is what the corpus is. On the conversion Post, bare
formulae are 39% of the section: `alhamdulillah` alone appears 114 times, and a table that
answered them would be posting 114 identical acknowledgements into one comment section. The
organisation's own argument, already in `docs/reply-table-tiktok.md`, is that
*Aamiin. Semoga Allah permudahkan segala urusan tuan/puan* under a bare `alhamdulillah` is a
non-sequitur — the Commenter is not praying for anyone, they are acknowledging God. That argument
was right and it was filed under `OUT_OF_SCOPE`, a name that reads as a hole in coverage. It is
not a hole. It is the design working, and it is 61.1% of the work.

**Decision: a Comment that presents nothing addressed to the organisation receives no Reply, and
this is a recorded outcome rather than a failure to match. It is never an Escalation.**

## The vocabulary had to be split first, because one word meant two opposites

`GLOSSARY.md` defines a **Tail** as a Comment no Canned reply covers, *which therefore needs one
written for it*. The labelled set had been calling its 61.1% class `TAIL` — a Comment that
needs no reply. The glossary's Tail and the label `TAIL` differed only in case and meant opposite
things, which is a collision no policy can be written on top of. Settling the policy and settling
the vocabulary are the same act.

- **`NO_REPLY`** — the label, replacing `TAIL`. A Comment the organisation correctly does not
  answer: a bare formula, an emoji or sticker, a mention, a support tag, chatter between
  commenters. Silence is the outcome. Nothing is posted and nothing is escalated.
- **Tail** — unchanged in the glossary, and unchanged in the router: the Comment no Canned reply
  covers, which is a **gap** and is where the next entry comes from. Its Intent label is
  `OUT_OF_SCOPE`, measured at **1.8% of rows**.

The two are both unanswered and they are opposites in the only way that matters: one is the
design working and the other is the design failing. Only the second justifies writing a new entry.

## Why silence must not be routed to a human

The tempting alternative is to answer nothing but to *Escalate* everything unanswered, so that the
organisation still sees it. ADR 0014 already refutes this from the other direction: Escalation is
only safe while a human actually reads the sink, and a ladder that escalates a large share of a
section is not conservative, it is abandoned. **A sink carrying 61.1% of the corpus is a sink
nobody reads**, and it would take the 1.8% that genuinely needs a person down with it.

So the two unanswered outcomes have to be told apart, and told apart at runtime:

| outcome | what it is | what happens | measured |
|---|---|---|---|
| Canned reply | an entry is eligible above its threshold | the Reply is posted | 36.4% |
| Escalation | a person in difficulty with an ask; or the Router is uncertain or in conflict | nothing is posted; a human is shown it | small, and deliberately so |
| Tail | a Reply was warranted and no entry fits — condolence, complaint, testimony, a question the table does not hold | nothing is posted; **Escalated to a human**, because it is a gap to be closed | 1.8% |
| `NO_REPLY` | nothing addressed to the organisation | nothing at all | **61.1%** |

**A Tail Comment escalates; a `NO_REPLY` Comment does not.** The first is a hole the organisation
should see and can decide to fill. The second is noise, and showing it to a human is how the sink
stops being read.

## Silence is never how ambiguity is resolved

`docs/reply-routing.md` says ambiguity is never resolved by guessing and never by silence. That
stands, and this decision does not soften it. The distinction is what the Comment *is*, not how
unsure the Router is:

- A Comment with nothing to answer is **`NO_REPLY`** at any confidence. Silence is the correct
  outcome and confidence does not enter into it.
- A Comment the Router cannot read, or reads two ways, is **Escalated**. Silence is not available
  to it, however low the confidence — a person who asked something does not get dropped because
  the Router was unsure.

The failure this forbids is a `NO_REPLY` rule wide enough to swallow a plea. That is why the
`NO_REPLY` test is *"does this Comment present anything addressed to the organisation?"* and not
*"did any entry match?"* — an unmatched plea is a Tail Comment and escalates; it never becomes
silence by failing to match.

## Consequences

- **The coverage metric changes meaning, and the reply table's 36% `OUT_OF_SCOPE` figure was
  measuring the wrong thing.** 516 Comments matched no keyword. That is a fact about the keyword
  pass, not about the corpus: under the labelled set, 61.1% needed no reply, 1.8% were genuine
  gaps, and the real coverage gap is **twenty times smaller** than the table claimed and shaped
  differently — condolence for the deceased is 8 of the 14 gap rows, the single largest part of
  it. Every rate in that table is now superseded and is marked as such.
- **The new entries come from the Tail and never from `NO_REPLY`.** A `NO_REPLY` Comment is not
  evidence of a missing entry; it is evidence that the class is correctly excluded. Mining the
  bare formulae for new Variants would grow the table in the direction of answering the 61.1%,
  which is the failure this ADR names.
- **Bare formulae stay out of `DOA_BLESSING` and out of every entry's Variants.** `alhamdulillah`
  is not a misspelling of a blessing to answer. It was already the table's reading; it is now a
  rule with a measured class behind it.
- **The Adapter decides `NO_REPLY` from the Comment's own shape, before the Router is consulted,
  and the Router's confidence cannot override it.** The test is structural: a bare formula or
  interjection, an emoji-only or sticker-only Comment, a mention or support tag, or a thread
  between two commenters. `tools/normalize.py` already carries `bare_interjection()` and
  `is_empty()` for exactly this, and they are how the class is identified in the corpus.
- **A `NO_REPLY` Comment is still recorded.** The Replied set exists so that nothing is handled
  twice (ADR 0007); a Comment the agent decided not to answer has been handled. Recording the
  decision is also what makes the class auditable — silence is indistinguishable from a crash
  unless the decision to stay silent was written down.
- **Most of the corpus never reaches Jev.** Because the `NO_REPLY` test is structural and runs
  before routing, **61.1% of Comments cost no Router call at all** — the working set is the 36.4%
  that can be answered. `docs/research/router-cost.md` already concludes that cost is not a
  constraint at any volume under consideration (about $0.021 per 1,000 Comments), so this does not
  rescue an unaffordable design; it removes roughly three-fifths of the calls that note prices, and
  the saving is a consequence of this decision rather than a reason for it.
- **`NO_REPLY` is not a licence to lower anything else.** It does not widen Escalation, does not
  raise a threshold, and does not make a near match postable. ADR 0019 sets the other half: what
  happens when the Router *is* unsure, and why none of it reaches a Post.
