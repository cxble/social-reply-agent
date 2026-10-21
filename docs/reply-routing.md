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
| `approved_reply` | the exact text Jev is allowed to select |
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

## Language

v1 ships English and Malay. Chinese and Tamil are earned by mining rather than assumed.
