# social-reply-agent

Replies to comments on the user's own social posts, automatically, using browser
automation because official platform APIs are out of scope.

## Language

### The things being acted on

**Post**:
A piece of content the user published on a Platform.
_Avoid_: video, upload, content

**Discovery window**:
The recency boundary that decides which Posts a Comment pass may notice for the first time. It bounds discovery rather than coverage: a Post is noticed while it is inside the window, and a Post never noticed while young is never noticed at all.
_Avoid_: lookback, scan range, freshness window

**Tracked post**:
A Post the agent has noticed and keeps watching, which stays tracked after it ages out of the Discovery window so that later Comments on it are still seen. Tracking ends when its eligible Backlog is resolved or the Post is closed.
_Avoid_: monitored post, watched post, target, record

**Comment**:
Text someone else left on a Post.
_Avoid_: reply, response, message

**Comment identity**:
The Platform's own identifier for a Comment, which the Replied set keys on. It is durable across Comment passes, but it does not necessarily locate the Comment on the page, so finding a Comment again is a separate problem from recognising it.
_Avoid_: comment ID, key, hash, fingerprint

**Commenter**:
The person who left a Comment.
_Avoid_: user, follower, fan, account

**Reply**:
The agent's public response to a Comment.
_Avoid_: response, answer, message, comment

**Platform**:
TikTok, Facebook, Instagram, or YouTube. A distinct site with its own Account and its own Adapter.
_Avoid_: channel, network, site, social

**Account**:
The user's identity on one Platform.
_Avoid_: profile, login, user

### Choosing what to say

**Reply table**:
The fixed set of approved Canned replies, one of which is chosen for each Comment.
_Avoid_: rules, templates, macros, playbook

**Canned reply**:
One entry in the Reply table. Text written and approved in advance.
_Avoid_: template, macro, script

**Phrasing**:
One of the approved texts a single Canned reply may post. Every Phrasing of a Canned reply states the same facts; they differ only in wording. Which one is posted rotates, so the same text does not repeat.
_Avoid_: variant, alternative, version, wording

**Phrasing set**:
The Phrasings that rotate together. Rotation is per set rather than per entry, so two entries naming the same set — as the donation and zakat entries do — share one rotation and cannot post the same text back to back on one Post.
_Avoid_: deck, pool, rotation group

**Variant**:
An observed spelling, abbreviation or slang form that a Canned reply treats as matching it. Variants are added only from real Comments, never guessed.
_Avoid_: alias, synonym, typo, fuzz

A Variant is how a Comment is **spelled**; a Phrasing is how a Reply is **written**. They sit at
opposite ends of the pipeline and are never the same kind of thing.

**Intent**:
The kind of situation a Comment presents, which decides which Canned replies are eligible for it.
_Avoid_: category, topic, class, label

**Normalization**:
The step that rewrites a Comment's text into a canonical form for matching, leaving the Comment as stored untouched.
_Avoid_: cleaning, preprocessing, canonicalisation, stemming

**Tail**:
A Comment no Canned reply covers but which a Reply was warranted for — the coverage gap, and where
the next entry comes from. The reply table spells its Intent `OUT_OF_SCOPE`.
_Avoid_: miscellaneous comment, edge case, fallback

**No-reply Comment**:
A Comment the organisation correctly does not answer, because it presents nothing addressed to the
organisation — a bare formula, an emoji or sticker, a mention, a support tag, chatter between
commenters. A No-reply Comment and a Tail Comment both go unanswered, and they are opposites in the
only way that matters: one is the design working and the other is a gap in it.
_Avoid_: junk, noise, unanswered comment, skipped comment

**Router**:
The step that assigns each Comment one of four outcomes: a Canned reply, an Escalation, the Tail, or
No reply.
_Avoid_: classifier, matcher

**Entry threshold**:
The confidence below which a Canned reply is not eligible for a Comment (`minimum_match_threshold`).
It is per entry and tiered by what a wrong Reply costs. Below its threshold the Comment is unmatched
and takes the unmatched path; the entry is not eligible at any lower confidence.
_Avoid_: cutoff, score, minimum match

**Help threshold**:
The much lower bar at which evidence of a person in difficulty, plus any kind of ask, raises a
human's hand. It gates Escalation and never posting, and it is deliberately set to catch rather than
to be precise.
_Avoid_: escalation threshold, safety threshold

**Evaluator**:
A check a written Reply must pass before it is posted.
_Avoid_: evaluation agent, judge, reviewer, guard, validator

**Verdict**:
An Evaluator's recorded answer about one Reply. Verdicts are kept, because they are what makes Graduation auditable rather than asserted.
_Avoid_: score, result, judgement, rating

**Escalation**:
Leaving a Comment for the user to answer rather than replying to it.
_Avoid_: handoff, deferral, review queue

### Running it

**Comment pass**:
One sweep over a Platform's Posts, looking for Comments that have not been answered.
_Avoid_: poll, cycle, scan, run

**Active window**:
The stretch of each local day during which a Platform agent may start work. Nothing new begins outside it, so the agent's activity matches the Account's waking hours instead of running around the clock.
_Avoid_: schedule, hours, uptime, business hours

**Backlog**:
Eligible Comments that have been discovered and are waiting for a Reply, including those that arrived while the agent was outside its Active window. It is not the Baseline: a Baseline Comment is never eligible, and a Backlog Comment is waiting.
_Avoid_: queue, todo, pending, worklist

**Platform agent**:
The long-running agent that drives one Platform. There is one per Platform.
_Avoid_: bot, worker, driver

**Adapter**:
The Platform-specific part of a Platform agent: the code that knows that Platform's pages.
_Avoid_: driver, connector, integration, scraper

**Draft mode**:
A mode in which a Platform agent prepares Replies for the user to send by hand, and posts nothing. Unlike a Dry run, a Platform can stay in draft mode indefinitely.
_Avoid_: approval queue, review mode, manual mode

**Dry run**:
A mode in which a Platform agent decides what it would post, records it, and posts nothing.
_Avoid_: shadow mode, test mode, preview

**Graduation**:
The point at which a Platform agent leaves Dry run and starts posting. It is earned by a run of Verdicts, not granted by a decision.
_Avoid_: promotion, go-live, activation

**Daily cap**:
The maximum number of Replies one Platform agent may post in a day. The count survives a restart, so restarting the agent cannot buy more Replies. It bounds the total, not the rate.
_Avoid_: rate limit, throttle, budget

**Pacing**:
The enforced spacing between Replies, so that a Platform agent's activity presents as a person working through Comments rather than a machine emptying a queue. It is separate from the Daily cap: the cap bounds how many Replies a day, and Pacing bounds how fast they arrive.
_Avoid_: delay, interval, sleep, jitter

**Kill switch**:
The single control whose presence stops all posting, on every Platform.
_Avoid_: pause, circuit breaker, emergency stop

**Replied set**:
The durable record of which Comments have already been handled, so that none is handled twice.
_Avoid_: seen set, dedupe store, cache, ledger

**Confirmation**:
The check that a Reply was posted against the Comment it was meant for, by comparing the identifier on the page with the one held.
_Avoid_: verification, assertion, receipt

**Reconciliation**:
Checking what the Replied set records against what is actually on the Platform, to catch a Reply that landed without being recorded, or a record with no Reply behind it.
_Avoid_: audit, sync, drift check

**Seeding**:
Reading a Platform's pages once, at activation, to establish the Baseline. Its rules are its own, and Reconciliation must not be run through it.
_Avoid_: import, backfill, bootstrap, initialisation

**Baseline**:
The Comments already on a Platform's scanned Posts when the agent was first activated. None of them is eligible for an automatic Reply, whether or not it carries a Reply.
_Avoid_: backlog, seed set, initial state, snapshot

**Reply status**:
What the page shows about whether a Comment has been answered: by the Account, by someone else, or unknown. It is held separately from Baseline membership, because an absent Reply is not evidence that a Comment is waiting for one.
_Avoid_: handled flag, done, answered

### Session and risk

**Session**:
The logged-in browser state for one Account. It is the credential, because there is no token.
_Avoid_: login, cookies, auth

**Flag**:
A Platform's judgement that an Account is automated, and the restrictions it places in response. Pacing and the Daily cap exist to avoid it. It is not the same failure as a dead Session: an Account can be flagged while its Session is perfectly alive, and an agent that only checks whether pages still load will miss it.
_Avoid_: ban, block, strike, suspension

**Selector rot**:
A locator that still matches an element, but now the wrong one.
_Avoid_: breakage, brittleness, deprecation

**Recorded page**:
A saved copy of a Platform's page, used to develop and test an Adapter without touching the live site.
_Avoid_: fixture, mock, snapshot, stub

### External

**Jev**:
TypeSafe's System One model, reached through OpenRouter. It returns typed decisions over the options supplied to it and cannot generate text, which is why it is the Router and the Evaluators, and never the author of a Reply.
_Avoid_: LLM, model, AI, classifier
