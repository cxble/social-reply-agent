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
| **Acknowledgement** | `DOA_BLESSING`, `DOA_REQUEST`, `GREETING`, `PRAISE_ENCOURAGE`, `BENEFICIARY_THANKS`, `CONVERT_CONGRATS` | **0.80** | Every one is written to be safe when wrong — short, warm, claiming no process, no address, no ruling, no promise of action. But the measurement (below) shows this tier is the *only* one that posts into silence: at 0.65 it posted **75 false replies on silence (112 rows)**, every false reply in the configuration. A public non-sequitur is not "a slightly off warm sentence", so the tier's cost was understated and its bar is raised from two-to-one to **four-to-one**. This is a judgment against the measured curve, not a value the curve forces: no threshold in the range drives the false replies to zero (0.95 still posts 4). |
| **Escalation gates** | `HELP_REQUEST`, `JOIN_ENQUIRY` | **0.20** | These hold no text. They raise a human's hand, and their bar is the **help threshold**, set to catch rather than to be precise (ADR 0014, ADR 0016): a false positive costs a human one skim, a false negative posts a membership link under a plea for help. The cost of catching is small — **0.4% of rows**, and the boundary set holds five `HELP_REQUEST`s of which **four do not appear in the random sample at all**, so the true rate is higher than the sample shows. |
| **Floor** | every entry, any tier | **0.50** | Below this an entry is eligible on a reading the Router itself thinks likelier wrong than right. With 61.1% of the corpus needing silence, that is exactly how a non-sequitur gets posted. No entry may be configured below the floor. |

**`DOA_REQUEST` belongs to the Acknowledgement tier, and an earlier version of this table left it
out.** The approval record's own Intent table gives its outcome as **Canned reply**, and its four
rows "promise no action beyond the doa itself" — so a wrong one costs exactly what the rest of the
tier costs, a slightly off warm sentence with no fact and no address in it, and it cannot be a gate
because a gate holds no text. The placement is settled by this row. It carries the tier's number,
revised to **0.80** by the measurement below, and the **34.9%** above measures the classes the
corpus pass could count — `DOA_REQUEST` is the one the document marks *undercounted*, so the tier
is at least that large, not smaller.

Below its threshold, an entry is simply not eligible, so the Comment is unmatched and takes the
unmatched path: a **Tail Comment escalates** (a reply was warranted and none fits — a gap to
close), and a Comment with nothing addressed to the organisation is `NO_REPLY` (ADR 0018). Silence
is not available to a Comment that asked something.

**The numbers are now measured against the corpus, and the measurement moved one of them.**
`tools/run_router_sweep.py` drove Jev over the 401 distinct Comments of the random set (401 calls,
~$0.0093), and `tools/score_threshold.py` replayed the recorded confidences through `Matcher` at
every threshold. On the shipped configuration the Acknowledgement tier — and only it — posted
false replies on silence, so its bar is **revised from 0.65 to 0.80**; the other two tiers are
**confirmed**, with the thin tier named below.

**Jev is not deterministic across calls, and the figures carry that variance.** Two sweeps over
the same 401 Comments sent byte-identical request bodies (the threshold is not in the body — only
the reply ids and their `matching_criteria` are) and returned different probabilities for **302 of
401** Comments, a different chosen reply id for 15, and a different kind (a decline vs a choice)
for 2. This contradicts the determinism measured in #8 and means the figures are approximate, not
exactly reproducible. **The kept artifact — `data/candidates/router.decisions.jsonl` — is the
second sweep; the first sweep's numbers are recorded here only, and are not the file on disk:** the
Acknowledgement tier's false replies on silence measured **77 (114 rows)** in the first sweep and
**75 (112 rows)** in the second, and the 0.80 figures **49 (85 rows)** and **48 (77 rows)**. The
direction is stable across both runs, which is what the revision rests on; a reader re-running the
sweep should expect a Comment or two to move, not an identical number.

The figures below are over the 351 Comments not answered by a declared Variant; the other 50 are
answered at confidence 1.0 by construction and are not evidence about any threshold. Each figure
is given twice — distinct Comments and corpus rows — because the labelling unit is the distinct
Comment while the percentages above are row-weighted. **The table is reproduced by
`python3 tools/score_threshold.py` against `data/candidates/router.decisions.jsonl`; a fresh sweep
will differ in the last digits because of the non-determinism this paragraph records.**

| tier | verdict | figure |
|---|---|---|
| **Consequential** | **0.90 — confirmed** | Scored gold population **1 distinct Comment** (1 row). It posted that one and posted nothing into silence. The tier is too thin to validate a number (AC 5). |
| **Acknowledgement** | **0.65 → 0.80 — revised** | At 0.65: **75 false replies on silence (112 rows)** — 69 `NO_REPLY` (106 rows) and 6 `OUT_OF_SCOPE` (6 rows) — the whole configuration's false replies; coverage **0.680** (132/194 distinct; 133/195 rows); precision **0.894** (118/132 distinct; 119/133 rows); 14 wrong-Intent posts. Raising to 0.80 cuts the false replies to **48 (77 rows)** and lifts precision to **0.949**, at coverage **0.505** (98/194 distinct; 99/195 rows). |
| **Escalation gates** | **0.20 — confirmed** | Nothing posted against a gate (`HELP_REQUEST`/`JOIN_ENQUIRY`): 0 of 351. Scored gold population **0 distinct** — both `JOIN_ENQUIRY` Comments are Variant hits — so the gate is thin (AC 5). |

**No threshold in the tested range removes the false replies on silence.** The global curve falls
smoothly — false replies on silence at **104/141** (distinct/rows) at 0.50, **75/112** at 0.65,
**48/77** at 0.80, **12/12** at 0.90, **4/4** at 0.95 — so the curve is *not* the step function a
pure argmax over extreme confidences would give, and there is no clean point that keeps the
acknowledgement coverage while silencing the non-sequiturs. 0.80 is therefore a judgment against
the curve, not a value the curve forces: the Acknowledgement tier's own number, raised from
two-to-one to four-to-one on the figure that at two-to-one it posts 75 false replies on silence.
What stands in front of these in production is **Bar 1** (`agent/no_reply.py`), which runs outside
the sweep, before the Router; the figure here is the Router and threshold layer's propensity to
post into silence, **not** a claim that production would post, and it is not licence to move Bars 1
or 4. The 0.90 tier was expected to be the sensitive one; the measurement puts the
damage in the 0.65 tier instead, where the corpus is largest.

**Bar 1 does not catch all of this, and the residue names the next fix.** Of the **48** false
replies on silence at 0.80, **10 distinct (31 rows)** are already refused by `no_reply_reason`
(`agent/no_reply.py`, the bare-formula test) and **38 distinct (46 rows)** are reachable by the
Router and threshold layer: **34 gold `NO_REPLY`** and **4 gold `OUT_OF_SCOPE`**. The reachable
`NO_REPLY` are formula **misspellings Bar 1's vocabulary lacks**, so they are a gap in
`agent/normalize.py::bare_interjection`, not a Router or threshold error; only the ~4
condolence-class `OUT_OF_SCOPE` posts are genuinely the threshold's business. The consequence is the
most actionable thing this run produced: **the next fix for this bucket belongs in the Bar-1
vocabulary, not in a tier number.** This does not change the revision; it makes the figure
interpretable, and it is what AC 2's "a refusal is the correct outcome" reasoning needs. The
decomposition is printed by `tools/score_threshold.py` (its "Bar 1 decomposition" section), so it
is re-checkable from the same artifact as the table above.

**Two tiers are too thin to be worth configuring, and are named rather than folded into a number
(AC 5): the Consequential tier (0.90), with 1 distinct scored gold Comment, and the Escalation
gates tier (0.20), with 0.** The labelled set's own criterion is that a class counted in single
digits cannot carry a rate — the random set is 401 of 839 distinct Comments (48%) and a 0.3%
Intent's interval contains zero (`docs/labelled-set-tiktok.md`, Limits). Both are reported as too
thin to be worth configuring, not editorialised into their numbers.

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
