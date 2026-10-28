# The hand-labelled set — TikTok

**564 distinct Comments from the harvest, each given the Intent it actually is.** They were drawn as
692 candidates — 128 Comments fall in both sets and were labelled twice, once per pass. This is the
ground truth `minimum_match_threshold` has to be calibrated against. `docs/reply-table-tiktok.md`
records what the corpus *contains* and what each entry's text should be; this document records what
each Comment *means*, which no keyword pass can measure.

Labelled 2026-10-21 against the eleven Intents of the reply table plus two non-Intents.

## Where the data lives, and why it is not in this repository

The labels are in `data/candidates/`, which `.gitignore` excludes. That is deliberate and it is the
same reasoning as `tools/prepare_corpus.py`: this repository is public, a Comment's text is already
public on the Platform, but an archive of 1,423 Comments paired with handles — or carrying a
per-person label like `HELP_REQUEST` — is a different artifact from the Comments sitting on TikTok.
It aggregates people and it is indexed. **The scripts that read the data are committed; the data is
not.** So the method, the sizes and the aggregate results are here, and the per-Comment labels are
not.

## Method

### The labelling unit is the distinct Comment, not the row

1,423 rows are **839 distinct Normalized Comments** (`tools/prepare_corpus.py` adds `norm`;
`data/corpus.jsonl`). That is the unit: `alhamdulillah` appears 114 times and is **one** decision,
not 114. Every candidate carries its own row count, so a label can be weighted back to the corpus.

Normalization is the fold `docs/reply-routing.md` describes — `semuga`/`smoga`/`smg`/`moga` →
`semoga`, and so on — with 3+ character repeats collapsed before the dictionary runs. The Comment
as stored is never touched.

### Two sets, drawn separately, because they answer different questions

| set | drawn | answers | must not be used for |
|---|---|---|---|
| `random` | 401 distinct Comments, stratified by Post and weighted to that Post's rows | **how often** each Intent occurs — the base rates | finding boundary cases; they are rare here by construction |
| `boundary` | 291 distinct Comments, **every** member of the contested families | **where the boundary is** | any base rate — it is enriched on purpose |

Those families — the `doa kan` / `tolong doa` form, `nak join` / `nak mohon` versus a plea,
`fitrah` / `sedekah` / `zakat` / `infaq`, a third party's illness inside a blessing, `bantu` /
`tolong`, `terima kasih`, `sumbang` / `akaun`, `masuk islam` / `mualaf` / `hidayah`, `salam`,
`terbaik` / `mantap`, the English markers and the `macam mana nak bantu` class, plus two catch-alls
for bare formulae and emoji-only Comments — are where two Intents collide or where one is easy to
invent.

**128 Comments fall in both sets.** They were labelled in two passes — boundary first, random
second, hours apart — and **all 128 agree**. That is a real consistency check on the rules below,
and it is the reason to trust them: the calls did not drift between passes.

Mixing the two sets would make every rate wrong. Keeping them apart is the whole design.

### The vocabulary, and the one distinction the reply table did not have

The eleven Intents, plus two non-Intents:

- **`NO_REPLY`** — matches nothing, and **no reply is the correct outcome**.
- **`UNCERTAIN`** — the reading is genuinely undecided. Kept rather than forced: a large
  `UNCERTAIN` count would be a finding about the Intent set, and guessing would destroy exactly the
  information the set exists to hold.

`NO_REPLY` and `OUT_OF_SCOPE` are **not the same thing**, and the reply table's 36% `OUT_OF_SCOPE`
figure conflated them:

- `NO_REPLY` — silence is the design working. A bare `alhamdulillah`, an emoji-only Comment, a
  drive-by `hadir support`.
- `OUT_OF_SCOPE` — a reply was arguably warranted and **no entry fits**. A condolence, a complaint
  about the aid process, a personal testimony, a question addressed to the organisation that the
  table does not answer.

Only the second is a coverage gap. **This was raised here as a candidate for an ADR and is now
ADR 0018**, which settles it and also settles the name: the class is `NO_REPLY` rather than `TAIL`
because the glossary's **Tail** is the *gap*, and the earlier label differed from it only in case
while meaning the opposite. ADR 0018 settles the outcome too — `NO_REPLY` receives nothing at all
and is **never Escalated**, while a Tail Comment is Escalated, because routing 61.1% of a corpus to
a human is how the Escalation sink stops being read (ADR 0014's own warning).

### The rules the labelling settled on

Written down because they are what make the 128-repeat agreement meaningful:

1. A blessing formula directed at the organisation or a named person → `DOA_BLESSING`. A
   first-person wish (`semoga saya…`, `semoga kami…`) is not addressed to anyone and → `NO_REPLY`.
2. `terima kasih` directed at the organisation → `BENEFICIARY_THANKS`, even when the commenter is
   not themselves a beneficiary. Thanks directed at God, or at other commenters, does not count.
3. A bare formula, emoji-only, a support tag, a mention, or off-topic chatter **between commenters**
   → `NO_REPLY`. The organisation should not enter a commenter-to-commenter thread.
4. `CONVERT_CONGRATS` requires the Comment to be addressed to or about the convert. A greeting to
   a new Muslim (`assalamualaikum saudara baharu`) is a `GREETING`; a general remark about Islam
   being the natural religion is `NO_REPLY`.

## Results — `random`, the base rates

401 distinct Comments, 769 rows. Row-weighted, which is a ratio estimate and approximately unbiased
because the draw was uniform over distinct Comments within each Post.

| label | distinct | rows | share |
|---|---|---|---|
| `NO_REPLY` | 143 | 470 | **61.1%** |
| `DOA_BLESSING` | 121 | 136 | 17.7% |
| `GREETING` | 46 | 56 | 7.3% |
| `PRAISE_ENCOURAGE` | 34 | 45 | 5.9% |
| `BENEFICIARY_THANKS` | 23 | 28 | 3.6% |
| `OUT_OF_SCOPE` | 14 | 14 | 1.8% |
| `DOA_REQUEST` | 10 | 10 | 1.3% |
| `CONVERT_CONGRATS` | 3 | 3 | 0.4% |
| `DONATION_ENQUIRY` | 2 | 2 | 0.3% |
| `JOIN_ENQUIRY` | 2 | 2 | 0.3% |
| `UNCERTAIN` | 2 | 2 | 0.3% |
| `HELP_REQUEST` | 1 | 1 | 0.1% |
| `ZAKAT_SEDEKAH_ENQUIRY` | **0** | **0** | — |

## What this changes in the reply table

**1. `OUT_OF_SCOPE` was never 36%.** The table's 516 was Comments that *matched nothing* — 231 bare
formulae and 285 textless. Under the labelled set those are `NO_REPLY`: correctly silent, not a gap.
`OUT_OF_SCOPE` proper is **1.8%**, and its members are testimony, condolence and complaint. The
table's own argument — that a bare `alhamdulillah` must not be answered with `Aamiin` — was right;
what was wrong was filing that decision under a name that reads as a hole in coverage.

**2. The corpus is mostly silence.** 61.1% of rows need no reply. Any design that replies to
everything is posting a non-sequitur into the majority of a comment section. This is the strongest
argument in the set for a high `minimum_match_threshold`, and it is now a measured number rather
than a suspicion.

**3. `ZAKAT_SEDEKAH_ENQUIRY` is confirmed empty.** Zero in the random sample and zero in the
boundary set, where an exhaustive sweep for `fitrah`, `sedekah`, `zakat` and `infaq` found four
keyword hits and all four were false — three using `fitrah` in its ordinary sense and one
`sedekah kan al-Fatihah` for a deceased person. The table reached this from a keyword pass; the
labelled set reaches it from reading every one of them. The entry keeps its Canned reply, because
an enquirer who does come must not be met with silence, but **`fitrah` and `sedekah` must not be
its keywords** — the entry carries a bank account.

**4. `HELP_REQUEST` is 1 in 401.** The table measured 4 real out of 41 keyword hits; the labelled
set puts the true rate at **0.1% of rows**, and the boundary set holds five `HELP_REQUEST`s of
which **four appear nowhere in the random sample**. Two things follow. First, the keyword pass was
not merely imprecise — it was hitting an
Intent that barely exists in this corpus. Second, the asymmetry the table argues for is now
quantified: the reply to `DONATION_ENQUIRY` carries an account number, so a plea landing there
publishes the bank details to someone asking for welfare help, and that error is unrecoverable
while a missed plea is merely late.

**5. `DOA_BLESSING` is 17.7%, not 26%.** The table's 364 was a keyword count over a truncated
corpus; the labelled set reads a sample. The entry stands, with the third-party illness class
(`semoga cepat sembuh`, `syafakallah`) inside it rather than beside it: of the 68 distinct Comments
the boundary set swept for `sembuh`/`syafakallah`/`sihat`, **61 are `DOA_BLESSING`** — the other
seven carry an explicit thanks or praise as well, which is the rule in § Method doing its work.

**6. Three classes the Intent set does not hold**, each found by reading rather than by keyword:

- **Condolence and recitation for the deceased** — `al-Fatihah buat arwah`, `salam takziah`,
  `Innalillah`. **Eight of the fourteen `OUT_OF_SCOPE` rows** in the random sample are this, and the
  boundary set's zakat false positive was one too. There is no entry and arguably should not be one,
  but the Adapter must not route it anywhere: a `DOA_BLESSING` reply under a bereavement is the
  wrong reply. It is the single largest component of the corpus's genuine coverage gap.
- **`stated disability, no request`** — the two `UNCERTAIN` rows. A commenter describes being OKU,
  or years of stroke, and never asks for anything. It may be a plea, or it may be testimony; the
  table's own `HELP_REQUEST` keyword pass swept this family in without noticing. It is the sharpest
  boundary in the set, and it is where a low threshold does its damage.
- **Comments not in Malay at all** — Bengali, Thai, Chinese, Arabic. A Buddhist blessing for a
  sick person is semantically a `DOA_BLESSING`, and every entry in the table is Malay-only. The
  labels record the intent and the note records the language; no entry can serve them.

## The harness, and the numbers it measured

`tools/run_router_sweep.py` drives Jev over the labelled set and records one decision per Comment:
which of `choice`/`declined`/`uncertain`/`failure` the call produced, plus a Variant hit, which
makes no Router call at all. `tools/score_threshold.py` then reads the labelled set and that
decisions file and replays the recorded confidences through `agent.matching.Matcher` — it decides
nothing itself. It reports **coverage**, **precision**, and — separately — **false replies on
silence**: Replies posted to a Comment whose correct handling is no Canned reply at all, which
under ADR 0018 is **both** `NO_REPLY` and `OUT_OF_SCOPE`. That third number is reported apart from
precision because averaging a public non-sequitur into a precision figure hides exactly the failure
the threshold exists to prevent. `OUT_OF_SCOPE` is not counted among the Comments that should get a
Reply: under ADR 0018 it must not receive one.

`--stub` generates synthetic decisions with a deliberate error rate, so the format, the curve and
the report are all exercised **before the Router exists**. Per `prove-the-path-you-havent-run`, a
mode switch is only a config change once the code behind it has actually run. The stub's output is
labelled SYNTHETIC on every run; its numbers describe the harness, not Jev.

### What the run measured

The real sweep ran over the 401 distinct Comments (401 calls, ~$0.0093). **50 Comments are answered
by a declared Variant with no Router call** (91 rows); they are reported separately and excluded
from the threshold figures. The remaining **351 Comments (678 rows)** carry a recorded decision.
Aggregate figures, each given twice — distinct Comments and corpus rows:

| figure | distinct | rows |
|---|---|---|
| Comments that should get a Canned reply | 194 | 195 |
| …that got one (**coverage**) | 98 (**0.505**) | 99 (**0.508**) |
| …that were posted correctly (**precision**) | 93 of 98 (**0.949**) | 94 of 99 (**0.949**) |
| **false replies on silence** (`NO_REPLY` or `OUT_OF_SCOPE`) | **48** | **77** |
| …`NO_REPLY` | 44 | 73 |
| …`OUT_OF_SCOPE` | 4 | 4 |
| posts against an Escalation gate (`HELP_REQUEST`/`JOIN_ENQUIRY`) | 0 | 0 |

Every false reply on silence came from the **Acknowledgement** tier; the Consequential and
Escalation-gates tiers posted none. `ZAKAT_SEDEKAH_ENQUIRY` was measured at zero in this set and
`DONATION_ENQUIRY` at one scored Comment (the other is a Variant hit), so the **Consequential tier
is too thin to validate a number** (1 distinct scored Comment) — as is the **Escalation gates
tier** (0 distinct; both `JOIN_ENQUIRY` Comments are Variant hits). ADR 0019 records the verdicts.

**These figures are the shipped configuration and are reproduced by
`python3 tools/score_threshold.py` against `data/candidates/router.decisions.jsonl`.** Jev is not
deterministic across calls (ADR 0019 records the variance), so a fresh sweep will differ in the
last digits. The revision rests on the *direction*, not the exact number: at the pre-revision
**0.65** the same artifact yields coverage **0.680** (132/194 distinct; 133/195 rows), precision
**0.894** (118/132 distinct; 119/133 rows) and **75 false replies on silence (112 rows)** — 69
`NO_REPLY` (106 rows) and 6 `OUT_OF_SCOPE` (6 rows) — where the shipped **0.80** yields the table
above.

**No threshold is picked here — the rule it is picked by is ADR 0019.** The sweep reports the curve;
choosing a point on it is a decision about which error is worse, and that decision is now recorded
rather than left open. ADR 0019 settles the *rule*: the threshold is per entry, tiered by what a
wrong Reply costs — **0.90** where the entry moves money, **0.80** for the acknowledgement classes,
**0.20** as the Escalation gate — with a **0.50 floor** no entry may sit below, and below its
threshold a Comment takes the unmatched path rather than being answered more cheaply. The measured
61.1% `NO_REPLY` is what argues for the floor, and the 0.3% size of the money-moving Intents is what
makes the 0.90 tier nearly free. The Acknowledgement number was **revised from 0.65 to 0.80** on the
measurement — it was the only tier posting false replies on silence (**75, 112 rows** at 0.65,
**48, 77 rows** at 0.80) — and no threshold in the tested range drives those to zero. What this set
supplies is the ground truth those numbers were re-derived against.

## Limits, stated plainly

- **The labels are my reading of Malay**, and the boundary cases are precisely where my reading is
  least reliable. Idiomatic distinctions — `makbulkan` versus `perkenankan`, whether
  `semoga dimurahkan rezeki` is addressed to the reader or to the world — are the ones a native
  speaker should check. The 128-repeat agreement shows internal consistency, not correctness.
- **The random sample is 401 of 839 distinct Comments** (48%), so a 0.3% Intent has a confidence
  interval wide enough to contain zero. `CONVERT_CONGRATS`, `DONATION_ENQUIRY`, `JOIN_ENQUIRY` and
  `HELP_REQUEST` are counted in single digits and cannot carry a rate.
- **The corpus is truncated on the large Posts and missing the last one or two.** The base rates
  describe what was read, not all of TikTok.
- **`minimum_match_threshold` is now measured, not derived from this document.** The Router exists
  (`agent/router.py`) and the sweep has run (`tools/run_router_sweep.py` + `tools/score_threshold.py`);
  ADR 0019 records the tier verdicts and the figures. What this document supplies is the ground
  truth those numbers were re-derived against, and the Limits above — the 401-of-839 sample, the
  single-digit classes — are why two tiers remain too thin to validate.

## Reproduce

```
python3 tools/prepare_corpus.py <raw-harvest.jsonl> data/corpus.jsonl
python3 tools/sample_for_labelling.py --report
python3 tools/sample_for_labelling.py --draw 400 250
python3 tools/apply_labels.py boundary data/candidates/labels/boundary.tsv
python3 tools/apply_labels.py random   data/candidates/labels/random.tsv
python3 tools/apply_labels.py random --report
python3 tools/score_threshold.py --stub
python3 tools/run_router_sweep.py          # network, opt-in: OPENROUTER_API_KEY
python3 tools/score_threshold.py           # replay the recorded decisions
```

The draw is seeded (`20261021`), so the same candidates come back. The labelling is not reproducible
by script and is not meant to be — that is the point of the set.
