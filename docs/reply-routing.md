# Reply routing

How a Comment becomes a Reply. Spec material, kept here so it does not live only in a conversation.

## Pipeline

1. **Receive the Comment.** The original text is preserved, and it is what a Reply answers.
2. **Normalize.** Recognise known Variants, meaning abbreviations, slang and misspellings, into a canonical form for matching. Normalization never alters the Comment as stored, and never replaces substrings in a way that could change meaning.
3. **Detect language.** Classify as Malay, English, mixed, or uncertain. A mixed or uncertain Comment is not forced into a class.
4. **Route.** Jev matches the Normalized Comment against the Canned replies eligible for that language and Intent.
5. **Evaluate.** Accept the Canned reply, send an unmatched Comment to the Tail, or Escalate.

## Reply table schema

| field | meaning |
|---|---|
| `reply_id` | stable identifier for the entry |
| `language` | the language of the approved Reply |
| `intent` | the Comment category this entry answers |
| `approved_phrasings` | the exact texts Jev is allowed to select, one of which rotation picks. Earlier documents spell the singular `approved_reply`, which is the first Phrasing — the entry's canonical text |
| `matching_criteria` | what Jev matches a Comment against |
| `known_variants` | validated Variants only |
| `minimum_match_threshold` | the confidence below which this entry is not eligible |

The table is version-controlled in git. Jev selects from it and never writes new text.

## Confidence

Temperature is not a matching signal. Jev exposes no temperature parameter and returns the same calibrated answer for the same state and questions, so the Router has no randomness to tune. Where a hosted model writes Tail text, its temperature governs writing and must never be read as a match.

Thresholds are per-entry, configurable, and calibrated against real Comments rather than guessed.

## Fallback

| Situation | Outcome |
|---|---|
| Known Variant, clear Intent, above threshold | the Canned reply |
| Language known, Intent unmatched | the Tail |
| Language uncertain, or meaning ambiguous | Escalation |
| Tail fails, or returns low confidence | Escalation |

A Reply is never invented to fill a gap.

### The help threshold

The `minimum_match_threshold` on an entry answers one question: *may a Canned reply be posted
for this Comment?* It is not the same question as *does a person need a human?*, and the two
must not share a number.

A second, deliberately lower **help threshold** answers the second question. Any evidence of a
person in difficulty — their own, or a named third party's — together with any kind of ask is
above it, at any confidence, and routes to Escalation regardless of how well some entry matched.

The asymmetry is the reason. A false positive costs a human one skim. A false negative posts a
canned membership link under a plea for help, in public, from an organisation whose purpose is
answering that plea. The help threshold is therefore set to catch rather than to be precise.

The cost of a low threshold is real and is recorded in ADR 0014: Escalation is only safe while a
human actually reads the sink. A ladder that escalates a large share of a section is not
conservative, it is abandoned.

### Disambiguation rules the corpus forced

- **Give or receive.** `nak mohon` asks to apply — to *join* the organisation, or *for
  assistance* from it. The words are identical. What separates them is whether the Commenter is
  offering their own effort or describing their own difficulty.
- **Tense and direction.** Thanks for help already given is answered; a request for help not yet
  given escalates. Hardship in the past tense inside a thank-you is not a plea.
- **Prayer or material help.** A request for doa is answered, and its reply promises no action.
  A request for material help escalates. "Is it a request?" does not distinguish them.
- **A location offered as context carries opposite meanings** depending on which question it
  answers, which is why none of these rules can be a keyword list.

Where none of these settle it, the Comment escalates. Ambiguity is never resolved by guessing
and never by silence.

## Variation

A Canned reply may hold several approved Phrasings, and rotation picks one per Reply.

Selection is a **shuffled deck per Canned reply, not a random draw.** Draw without replacement
until the deck is empty, reshuffle, and re-draw if the reshuffle would open on the Phrasing that
just closed. A uniform random choice over three Phrasings repeats back to back about one time in
three and clumps across a section, which is a pattern — just an irregular one. Even distribution
is less recognisable than randomness, not more.

Rotation state is durable and belongs to the Canned reply, not to a Comment pass, because what
is being avoided is repetition over time rather than within one sweep. It survives a restart,
like the Daily cap count: a rotation held only in memory restarts at its first Phrasing and
re-posts it.

**A Phrasing varies wording and never facts.** If two Phrasings of one entry can be told apart on
content rather than on phrasing, one of them is not a Phrasing of that entry. An entry with a
single approved text has a deck of one and no rotation, and an entry that Escalates has no text
to vary at all.

**Phrasings should be close variants, not far ones.** A person answering the same kind of Comment
twenty times says nearly the same thing with small differences, and that near-repeat is what a
person looks like. Widely differing Replies read as a phrasebook being sampled — a machine signal
in its own right, and louder than the repetition it avoids. The target is the smallest difference
that avoids an exact repeat.

Phrasings do not reduce Flag risk. They reduce a spam signal and the chance a reader concludes
they are reading a machine; the behaviour axis is Pacing and the Daily cap, and neither
substitutes for the other.

## Language

v1 ships English and Malay. Chinese and Tamil are earned by mining rather than assumed.
