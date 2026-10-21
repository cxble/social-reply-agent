# A join enquiry escalates

The corpus contains people asking how to become part of the organisation: `Sy nk join pertubuhan
ni boleh tak 😁`, `Saya nak join bleh x`, and a follow-up from one of them giving his location,
`kepala batas pulau pinang`.

This was first written up as an entry **blocked on facts** — the enquiry has a real answer and
the agent did not have it, so the entry sat empty waiting for the Account holder to say what
joining involves. The Account holder's decision on 2026-10-21 was to escalate instead.

**Decision: `JOIN_ENQUIRY` routes to Escalation. The agent posts nothing, and a human answers.**

**This resolves the blocking fact rather than answering it.** The entry was never waiting for
information the pipeline could not hold; it was waiting for a decision about who should give the
information. Escalating means the agent does not need to know how someone joins, because it is
not going to say.

The reason is different from ADR 0014's, and the difference is worth keeping straight:

- `HELP_REQUEST` escalates because **a Canned reply is harmful** — any text at all is the wrong
  answer to a plea, no matter how well the match scored.
- `JOIN_ENQUIRY` escalates because **the organisation is the right answerer.** A canned reply is
  not offensive here; it is simply not good enough. "How do I join" means a process: who to
  contact, what is needed, whether there is a fee, whether membership is open at all. `DM kami`
  is a non-answer that teaches the person the organisation does not reply. Membership is also
  the point at which a stranger becomes part of the organisation, which is a decision for the
  organisation and not for a table.

**Consequences.**

- **The hardest boundary in the table stopped mattering.** `JOIN_ENQUIRY` and `HELP_REQUEST`
  share `nak mohon` — *mohon* is "apply", and the same word names applying to join and applying
  for assistance — and the corpus holds one Comment of each that cannot be told apart by
  keyword. Both now escalate, so a Comment landing on the wrong one of the pair still reaches a
  human. Redesigning the Router to separate them precisely is no longer urgent.
- **It is not a licence to stop distinguishing them from everything else.** The same vocabulary
  appears in `DOA_REQUEST` — `doakan sy Kaya raya utk Bantu org lain` — which **is** answered,
  and on the Umrah Post it is the dominant Intent. So the give-or-receive test in
  `docs/reply-routing.md` still has work to do: it is what keeps a request for prayer out of the
  escalation pile. What changed is the cost of error *within* the pair. Between them, a mistake
  is now invisible rather than public.
- **This is the second Intent with no `approved_reply`, and the table's shape changed with it.**
  Two of eleven Intents now exist only to be recognised and handed on. That is worth watching:
  if the count keeps growing, the Reply table is becoming a triage table for a human, and the
  case for calling this an automated replying agent weakens.
- It adds volume to the Escalation sink, which ADR 0014 already says must be watched. Join
  enquiries are rarer than help requests in the corpus, but they are the kind a person sends
  when they are enthusiastic and waiting, so an unanswered one is a lost volunteer rather than a
  silently dropped plea. Both need the same thing: somebody reading.
- The Account holder may later decide to answer this with a single approved line — a contact
  address, a form URL. That would be a new entry in the table, not a change to this decision,
  and it would need the same treatment as `tt-donate-001`: verbatim, fixed, never paraphrased.
