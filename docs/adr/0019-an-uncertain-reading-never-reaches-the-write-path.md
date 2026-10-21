# An uncertain reading never reaches the write path

ADR 0018 settles what happens to a Comment nothing is addressed to: nothing. This decides the
other two ways a Reply can be wrong to post — the Router is unsure, or the Comment is not the one
the agent thinks it is — and it decides them as **bars a Comment must clear to be written to**,
rather than as a threshold tuned until the numbers look acceptable.

The corpus says the bar has to be high. **61.1% of rows need no reply at all.** A Router that
answers everything is posting a non-sequitur into the majority of a comment section, in public,
under the organisation's name, to people who were not talking to it. The measured base rate, and
not a preference for caution, is what makes the low-threshold case indefensible.

**Decision: a Canned reply may be posted only if the Comment clears all four bars below. Failing
one is not a near miss — the Comment falls to its correct non-posting outcome, and the wrong
Reply is structurally unavailable rather than merely unlikely.**

## The four bars

**1. The Comment is not `NO_REPLY`.** Structural, decided from the Comment's own shape before the
Router is consulted — a bare formula, an emoji or sticker, a mention, a support tag, chatter
between commenters (ADR 0018). **Confidence does not enter into it.** No score makes a bare
`alhamdulillah` postable, and no threshold change can admit one.

**2. The entry is eligible above its own `minimum_match_threshold`.** The threshold is per entry
and **tiered by what a wrong Reply costs**, not by how good the Router is. One global number would
either forfeit the acknowledgement classes the organisation most wants or expose the entries that
can move money.

**3. The Router is not uncertain and not in conflict.** `UNCERTAIN` is a recorded outcome it is
allowed to return, and it is kept rather than forced (the labelled set holds two such Comments —
"states a disability, asks for nothing", the sharpest boundary in the corpus). A Comment with two
mutually exclusive Intents both above threshold is a conflict, and the higher one is not chosen
(the reply table's rule). **Bar 3 is not a threshold**: lowering a number cannot admit an
`UNCERTAIN` Comment, because there is no score to lower.

**4. The Comment's identifier is confirmed at the moment of writing.** Immediately before submit,
the write path re-reads the identifier on the page and requires it to equal the identifier it
holds (ADR 0007's Confirmation). A Comment whose identifier cannot be read is **skipped and
Escalated, never matched on its text** — a content-hash fallback turns an edited Comment into a
new one and posts a second Reply, which is the largest correctness risk in this project.

## The tiers, and why the numbers sit where they do

The thresholds below are the defaults these rules produce. They are set by the cost of an error
and by the measured size of the class, because where a failure is unrecoverable and the class is
tiny, **precision is close to free**.

| tier | entries | threshold | why |
|---|---|---|---|
| **Consequential** | `DONATION_ENQUIRY`, `ZAKAT_SEDEKAH_ENQUIRY` | **0.90** | Both post a bank, an account number and a payee. A wrong one is unrecoverable and public: a plea landing here publishes the organisation's bank details to someone asking for welfare help. Together they are **0.3% of rows** — and all of that 0.3% is `DONATION_ENQUIRY`, since `ZAKAT_SEDEKAH_ENQUIRY` was measured at **zero** — so demanding near-certainty forfeits almost no coverage. |
| **Acknowledgement** | `DOA_BLESSING`, `GREETING`, `PRAISE_ENCOURAGE`, `BENEFICIARY_THANKS`, `CONVERT_CONGRATS` | **0.65** | Every one is written to be safe when wrong — short, warm, claiming no process, no address, no ruling, no promise of action. The error is a slightly off warm sentence, not a wrong fact. This tier is **34.9% of rows** and is the bulk of the work worth doing, so a bar high enough to forfeit it buys safety this tier does not need. 0.65 is "likelier right than wrong, about two to one". |
| **Escalation gates** | `HELP_REQUEST`, `JOIN_ENQUIRY` | **0.20** | These hold no text. They raise a human's hand, and their bar is the **help threshold**, set to catch rather than to be precise (ADR 0014, ADR 0016): a false positive costs a human one skim, a false negative posts a membership link under a plea for help. The cost of catching is small — **0.4% of rows**, and the boundary set holds five `HELP_REQUEST`s of which **four do not appear in the random sample at all**, so the true rate is higher than the sample shows. |
| **Floor** | every entry, any tier | **0.50** | Below this an entry is eligible on a reading the Router itself thinks likelier wrong than right. With 61.1% of the corpus needing silence, that is exactly how a non-sequitur gets posted. No entry may be configured below the floor. |

Below its threshold, an entry is simply not eligible, so the Comment is unmatched and takes the
unmatched path: a **Tail Comment escalates** (a reply was warranted and none fits — a gap to
close), and a Comment with nothing addressed to the organisation is `NO_REPLY` (ADR 0018). Silence
is not available to a Comment that asked something.

**These numbers cannot be validated against the corpus today, and saying so is part of the
decision.** They are claims about Jev's confidences, and the Router does not exist in this
repository. `tools/score_threshold.py` sweeps `minimum_match_threshold` against the 401-Comment
labelled set and reports coverage, precision and **false replies on silence** separately, but its
current output is generated by `--stub` and is marked SYNTHETIC on every run — it exercises the
path, it does not measure Jev. What is settled now is the **rule** (tiered by cost of error, with
a floor, and the ordering of the tiers) and these are its default numbers. What will move them is
Jev's real curve, and the specific evidence would be: false replies on silence above zero at any
tier, or a tier whose coverage at its own threshold is too thin to be worth the configuration.
The 0.90 tier is expected to be the sensitive one.

## The gate holds until identity and extraction are resolved

Bars 1–3 are about meaning. Bar 4 is about *which Comment*, and it is the one that cannot be
discharged today. The issues, all recorded in `docs/research/comment-identity.md` and in spec
issue #1's stories 8–11:

- **TikTok's `cid` is durable but not addressable.** The React-props path returned `cid: null` on
  every one of 228 harvested Comments; the identifier now comes from the page's own `comment/list`
  response, and holding it does not let the Adapter find the Comment it names. Identity and
  addressability are separate problems and only one of them is solved.
- **Facebook's `comment_id` anchor is frequently absent**, and every surveyed implementation falls
  back to a content hash — under which **an edited Comment looks new and receives a second Reply.**
- **Extraction is not trustworthy yet.** TikTok renders Comments only in a headed browser;
  selectors rotate between builds — `[class*="DivCommentItem"]` finds every Comment where
  `[data-e2e^="comment-level"]` now matches nothing, though those `data-e2e` parts still appear
  *inside* a Comment; and a read is complete only when its count agrees with `total` — `has_more: 0`
  is not evidence of completion, having been observed at cursor 60 with 50 of 2,712 Comments read.
- **No logged-in observation of any Platform exists**, which is the standing limitation under all
  of the above.

While a Comment's identity cannot be read and re-confirmed, the classification layer and the write
layer cannot be guaranteed to be discussing the same Comment. **So nothing uncertain is written:
`UNCERTAIN`, below-threshold, conflicting and unconfirmable classifications all stay out of the
automated write path until those four are resolved.** An uncertain Comment Escalates — a human
decides it — which is out of the write path too.

**What lifting the gate requires, stated checkably rather than as a judgement:** for every Platform
the agent posts to, (i) the Comment's own identifier is obtainable from the page or from the
page's own request; (ii) that identifier can be re-read on the page immediately before submit and
compared with the one held; (iii) an extraction pass reports its count against `total` and asserts
completeness; and (iv) a Recorded page exercises each of those without a Session and without
touching the live site. **Reaching those does not lift the gate automatically** — how far it may
then be opened is a further decision, made against the measured curve, and it is the Account
holder's.

## Consequences

- **The gate is not a threshold and cannot be tuned as one.** Bars 1, 3 and 4 are outside the
  sweep entirely. A report showing better precision at a lower threshold does not move them, and
  must not be read as licence to.
- **Uncertainty escalates; it never goes silent, and it never gets a guess.** This is ADR 0018's
  boundary from the other side: silence is for Comments with nothing addressed to the
  organisation, and a Comment the Router cannot read is not one of those.
- **The uncertain band is affordable precisely because it is measured.** `UNCERTAIN` is 0.3% of
  rows and the escalation-gated Intents are 0.4%, so a catch-everything help threshold does not
  flood the sink that ADR 0014 warns must stay readable. The same rule applied to the 61.1%
  `NO_REPLY` class would destroy it, which is why the two are decided separately.
- **The harness must count these bars, or it will flatter the Router.** Posting to a `NO_REPLY`
  **or** `OUT_OF_SCOPE` Comment is the worst error and both belong in *false replies on silence*;
  and `OUT_OF_SCOPE` must not be counted as a Comment that "should get a Reply", because under
  ADR 0018 it must not receive one. A coverage figure that counts it as a miss and a hit at the
  same time is measuring nothing. `tools/score_threshold.py` is corrected accordingly.
- **Dry run is where this is measured, not argued.** Every bar here is checkable from the record
  Dry run produces (spec story 45; posting is earned by Verdicts, story 46): the decision, the
  confidence, the tier, and which bar refused it. Graduation is earned against those Verdicts, and
  bars 1–4 are what the Verdicts have to show were applied.
