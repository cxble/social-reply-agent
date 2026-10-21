# A Reply states only facts the Account holder approved

ADR 0002 establishes that Jev selects Replies and cannot write them, so nothing generated
reaches a Post. That constrains *text*. It does not, on its own, constrain *facts*, and the
difference is where the risk actually lives.

A fluent reply that answers a question is written by a model, and a model that has seen a
thousand Malaysian welfare organisations will supply an account number, a joining procedure, an
office address, or a ruling on zakat with no sign that it is guessing. Nothing in the pipeline
marks that text as invented. ADR 0002's guarantee holds perfectly while the Reply confidently
sends a donor's money to a stranger's account.

**Decision: the agent may state only facts the Account holder has approved, and a Reply that
needs a fact the table does not hold is an Escalation rather than a Reply.**

Two entries in `docs/reply-table-tiktok.md` are shaped by this directly:

- **`tt-donate-001`** holds the Account holder's donation text **verbatim** — bank, account
  number and payee, exactly as supplied. It is not paraphrased, reformatted, reordered or
  reconstructed, because every one of those is a chance to change a digit. `tt-zakat-001`
  carries the identical text by the Account holder's decision, so the two entries duplicate on
  purpose and neither may be edited alone.
- **`tt-join-001`** was left empty under this rule — "how do I join?" has a real answer and the
  agent did not hold it, so no text could be written. The Account holder resolved it on
  2026-10-21 by escalating the Intent instead (ADR 0016), which is this rule's other exit: the
  agent does not need the fact if it is not going to state it.

Zakat was the case this rule was written for. Zakat is a religious obligation with rules about
who may receive it and how it is handled, and a model's summary of those rules, posted under a
registered organisation's name, is a religious error and not an awkward one. The Account holder
has since decided that a zakat enquiry gets the donation text, which states no rule and makes no
claim about the account — so the reply asserts nothing this ADR forbids. The residual question
of whether that account may validly receive zakat is the Account holder's to settle and is
recorded in the entry.

**Consequences.**

- The table is not merely a matching corpus, it is the **complete set of facts the agent may
  assert**. Anything not in it is unapproved by construction, and that is checkable: a Reply
  containing a number, a URL, an address or a procedure that does not appear in its entry is a
  defect, not a judgement call.
- This is what makes the Tail safe. The Tail is the one path where text is written rather than
  selected (ADR 0002), and the rule it must obey is that it may be warm, vague or short, but it
  may not be *informative*. `Aamiin, semoga dipermudahkan` is a valid Tail reply. A Tail reply
  that names a bank is not, however true the bank is.
- **A blocked entry is a question for the Account holder, not a prompt for the agent.** The
  correct response to a gap in the table is to ask, and the account holder supplied the donation
  text when asked. Two gaps remain.
- It also bounds the appeal of a larger model. As the Router's capability grows, the temptation
  to let it answer the join question and the zakat question grows with it, and this decision is
  what refuses that — not on capability grounds but because the organisation, not the model, is
  answerable for what it tells a blind man about how to get help.
- Where a fact is public and easily verified, this rule is still the rule. The organisation's
  ROS registration number, its address and its officers are all knowable and none of them are
  approved for posting, because knowable is not the same as approved and the failure mode of a
  stale or wrong one is identical.
