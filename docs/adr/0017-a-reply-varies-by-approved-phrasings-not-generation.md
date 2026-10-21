# A reply varies by approved Phrasings, not by generation

The Account holder's instruction on 2026-10-21: replies need variations, never duplicates, and
they should alternate so that no pattern is recognisable. The concern is what the same text does
over time — identical wording under every donation question for a year.

**Decision: a Canned reply may hold several approved texts — its Phrasings — and one is chosen
per Reply. Reply text is authored and approved in advance, and is never generated.**

## Why not generation

The obvious answer to "we need more variations" is a model that writes them. It was considered
and refused, and the reasons compound rather than merely adding up.

- **Jev cannot write text at all** (ADR 0002). It returns typed decisions over options supplied
  to it. Variation is therefore not something the Router can be asked for; it can only be asked
  to choose, which means the options must exist first.
- **ADR 0015 forbids a Reply from asserting anything the Account holder has not approved.** A
  generated variation asserts by construction — that is what generating prose *is* — so every
  generated sentence would be an unauthorised claim about this organisation, in public, under
  its name.
- **The entries where repetition is most visible are the ones where generation is most
  dangerous.** `tt-donate-001` is a bank name, an account number and a payee. A model asked to
  paraphrase it will reformat the digits, or "correct" the payee's name, or drift into inventing
  a second account "for zakat". The failure mode of a generated variation here is money sent to
  a stranger, not an awkward sentence.
- **A local model was the specific proposal, and it is the wrong shape of tool for this.** The
  machine has ~7 GB of RAM and no GPU, so a model that writes Malay well enough to be posted
  under the organisation's name is not one that fits. And the cheap model that *does* fit fails
  in exactly the unaudited way the third point describes. The trade is not fluency for cost; it
  is a wrong fact in public for a saved afternoon of writing.

So the variation is supplied the same way the rest of the table is: written, read, approved.

## What a Phrasing may vary

**A Phrasing varies register, framing and closing courtesy. It never varies a fact.** Every
Phrasing of a Canned reply asserts the same facts, or it is not a Phrasing of that reply.

This keeps ADR 0015 intact at the level of the entry rather than the sentence: an entry's facts
are settled once, and each Phrasing is a different way of saying those same facts. It also gives
a mechanical check — if two Phrasings of one entry can be told apart on content rather than on
wording, one of them is not a Phrasing and the entry is wrong.

For `tt-donate-001` and `tt-zakat-001` this means the block the Account holder supplied is
verbatim in every Phrasing. Text that may vary exists only *around* it, and adding that text is
the Account holder's decision, not a drafting one.

**Phrasings are deliberately close to one another, and this is the part most easily got
backwards.** "Variations" invites the reading *make them as different as possible*, which is
wrong. A person answering the same kind of Comment twenty times says nearly the same thing with
small differences; that near-repeat is what a human looks like. Text that varies *widely* from
one Reply to the next reads as a phrasebook being sampled, which is a machine signal in its own
right and a louder one than the repetition it was meant to avoid. **The target is the smallest
difference that avoids an exact repeat, not the largest.**

## Rotation is not randomness

"No pattern to be recognised" invites a random pick, and a random pick is the wrong mechanism.
A uniform choice over three Phrasings will repeat back-to-back roughly one time in three, and
over a section it clumps — which is a pattern, just an irregular one.

The mechanism is a **shuffled deck per Canned reply**: draw a Phrasing without replacement until
the deck is empty, reshuffle, and re-draw if the reshuffle would open on the Phrasing that just
closed. That cannot repeat consecutively, and it distributes evenly across any window a reader
might see. Even distribution is *less* recognisable than random, not more.

## Consequences

- **Rotation state is durable and shared, like the Daily cap count.** It has to survive a
  restart (the same requirement ADR 0009's count carries) and it is keyed on the Phrasing set
  rather than on the entry or on a Comment pass, because the thing being avoided is repetition
  over time, not within one sweep.
- **Rotation is per Phrasing set, not per entry, and the donation and zakat entries are why.**
  `tt-donate-001` and `tt-zakat-001` are separate entries holding the *same* text, so per-entry
  decks would let a Post carrying one donation question and one zakat question receive the
  identical reply twice — the duplicate this decision exists to prevent. The Account holder's
  ruling on 2026-10-21 is that donating and zakat are one thing here, so the two entries point at
  **one shared set**: one deck, and the second Reply in that situation draws a different
  Phrasing. Keying rotation on the set rather than the entry is what makes that expressible, and
  it is the general answer for any two entries that can answer Comments on the same Post.
  **It requires at least two Phrasings in the set** — a shared deck of one still posts the same
  words twice. The bank block stays verbatim in every Phrasing; only the courtesy line above it
  is drafted, and that needs the Account holder's sign-off.
- **The donation text is the case that keeps fact-invariance honest.** A Phrasing of
  `tt-donate-001` may reword the greeting and may not touch the bank, the number or the payee. A
  frame that says *sumbangan boleh disalurkan ke akaun berikut* asserts nothing the canonical
  text does not already assert; a frame that added a second account, or "corrected" the payee,
  would not be a Phrasing and would be the most expensive mistake this table can make.
- **One alternate is not enough to be worth having.** Two Phrasings produce a visible A/B
  alternation, which a reader notices faster than they notice repetition at low volume. Three or
  four is the working number.
- **Every Phrasing is approved text, so ADR 0015's sign-off applies to it identically.** The
  sign-off surface grows by roughly three texts per entry. That cost is real, it falls on the
  Account holder, and it is the price of not generating.
- **This is a content measure and not a Flag control.** Repetition carries two costs: platforms
  weigh duplicate text as a spam signal, and a reader who sees the same sentence under five
  comments concludes they are reading a machine. Phrasings address both. They do not address the
  behaviour axis, which is the one that carries the flag risk — Pacing and the Daily cap bound
  how fast and how many Replies arrive, and no amount of varied text substitutes for them. A
  varied agent posting every three seconds is more conspicuous than a repetitive one posting
  every forty-five. **Phrasings must not be recorded as a Flag mitigation, and must not be
  traded against Pacing.**
