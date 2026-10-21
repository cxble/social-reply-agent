# A help request escalates, and is never answered with a Canned reply

This Account belongs to a welfare organisation, and its comment section is where people in
difficulty ask it for help in public. **It is not a rare edge case: on the welfare-ziarah Posts
it is a substantial share of the section.** Six such Comments are in the harvested corpus of
2026-10-21:

> `saya OKU juga tak ada yg membantu.hospitel tk leh wat apa² saya penyakit saraf susah pergi mana² tak boleh pendengaran.adk beradik tnk ambil tahu masalah saya`

> `macam mana nak mohon. sy oku fizikal and now tgah hadapi risiko buta kekal. from klang`

> `MCM mna nak moham saya OKU pesakit stroke`

> `Sy oku fizikal sakit Parkinson deses dgn minor stroke sebelah kanan`

> `Bantulah Farina saudara Ben . Dia tak boleh uruskan dirinya.`

> `salam tuan, saya ank pulau pinang, tanjung tokong, mohon klu boleh tolong ziarah tanah2 perkuburan islam seminar penang`

Four of these are disabled people describing their own situation and asking to be helped — a
nerve condition with deafness and unhelpful siblings, approaching blindness, stroke, Parkinson's
with partial paralysis. One asks on a third party's behalf. The last asks for a family grave to
be visited.

The pattern is specific enough to name: **a public disclosure of disability, followed by a
request.** That is what makes this section different from a normal comment section, and it is
the reason this ADR exists rather than a paragraph in the table's notes.

**Decision: `HELP_REQUEST` is an Intent that routes to Escalation. The agent posts nothing on
such a Comment and a human answers it.**

It is deliberately **not** a Reply-table entry. It has no `approved_reply`, no Variants and no
threshold, because there is no text the agent is permitted to post. Writing one entry with an
empty reply would invite someone to fill it in later.

The reason it cannot be a Canned reply is that a Canned reply is chosen by matching, and
matching is exactly what fails here. Both Comments above contain `nak mohon` — the same words as
`Sy nk join pertubuhan ni boleh tak`, a routine membership enquiry that *should* be answered
with a link. The two are indistinguishable by keyword, share an Intent's vocabulary, and differ
only in that one of them is a person describing their own difficulty. A table that answers the
enquiry answers the plea with the same words.

**Consequences.**

- A Canned reply is wrong here no matter how well it matches, so the failure is not one a better
  threshold fixes. Raising the threshold until the plea stops matching also stops the enquiry
  matching, and the agent goes quiet on both.
- The cost is asymmetric and that is the whole argument. A missed enquiry is one unanswered
  Comment. An automated membership link posted under a blind man's plea for help is a public
  failure by an organisation whose stated purpose is helping him.
- Escalation is therefore the *only* outcome for this Intent, not the fallback when confidence is
  low. A high-confidence match on `HELP_REQUEST` still escalates.
- **The agent's silence is not the deliverable — the human's answer is.** An escalated Comment
  that nobody reads is the same as no system at all, so the Escalation sink has to be something
  the Account holder actually watches. This is the point at which the project depends on a
  person, and it is worth stating plainly rather than leaving implied.
- Anticipated but not yet in the corpus: a Comment asking the organisation to help a third party
  ("tolong keluarga saya"), and one offering help rather than asking. Both would route here until
  real Comments say otherwise.
- **"A request" is not the test.** The corpus also holds a large class of `DOA_REQUEST`
  Comments — `Tolong DOAKAN saya jgk utk ke sana`, `Doakan saya dan suami menjadi tetamu Allah`
  — which are requests too, and which **must be answered**, not escalated. On the Umrah Post they
  are the dominant Intent. So the rule cannot be "a request escalates"; it has to distinguish a
  request for prayer, which the community answers with `Aamiin`, from a request for material
  help, which a human must answer. Whatever else follows, that boundary is not a keyword.
- **What the test actually is: give or receive.** A `HELP_REQUEST` describes the Commenter's own
  difficulty, or a named third party's, and asks the organisation to act on it. A `JOIN_ENQUIRY`
  offers the Commenter's own effort and says nothing about their circumstances. The two share
  `nak mohon` — *mohon* is "apply", and the same word names applying to join and applying for
  assistance — so the vocabulary is not merely similar, it is the same word doing the same job in
  both. The confirming detail that this cannot be lexical: a location in a Comment
  (`kepala batas pulau pinang`) means "here is where I could join"; in another (`from klang`) it
  means "here is where I am, and I need help". Same fact, opposite meaning, decided entirely by
  a question the words do not answer.
- **This makes the threshold the wrong instrument, not merely a badly tuned one.** A single
  `minimum_match_threshold` asks whether a Canned reply may be posted. The question here is
  whether a human is needed, and it needs its own number, set low on purpose. Any evidence of a
  person in difficulty plus any kind of ask crosses it, at any confidence, and escalates even
  when some entry matched well. The two thresholds are recorded in `docs/reply-routing.md`.
- **A low help threshold is only safe while the sink is watched**, which is the same dependency
  this ADR already names. Escalating a large share of a section does not make the system
  conservative; it makes the human stop reading, at which point the system answers nothing while
  appearing to work.
- `BENEFICIARY_THANKS` borders this Intent from the other side. `terima kasih datang melawat ayah
  saya Dan bantuan pampers` contains hardship and a plea-shaped clause, and is a thank-you. Tense
  and direction separate them, and where they do not, this Intent wins.
- **`JOIN_ENQUIRY` joined this Intent in Escalation on 2026-10-21** (ADR 0016), which changed the
  boundary problem above from a routing risk into a non-issue: the two Intents that shared
  `nak mohon` now both escalate, so a Comment landing on the wrong one of the pair still reaches
  a human. The test in `docs/reply-routing.md` still matters for keeping `DOA_REQUEST` out of
  the escalation pile, since `doakan` and `nak mohon` appear in the same sections and only one
  of them is answered.
- Zakat, sedekah and infaq enquiries are a separate Intent and stay in the table, but they carry
  the same class of risk at lower intensity — see `docs/reply-table-tiktok.md`, where that entry
  is left unpopulated rather than guessed.
