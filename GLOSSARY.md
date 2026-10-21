# social-reply-agent

Replies to comments on the user's own social posts, automatically, using browser
automation because official platform APIs are out of scope.

## Language

### The things being acted on

**Post**:
A piece of content the user published on a Platform.
_Avoid_: video, upload, content

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

**Variant**:
An observed spelling, abbreviation or slang form that a Canned reply treats as matching it. Variants are added only from real Comments, never guessed.
_Avoid_: alias, synonym, typo, fuzz

**Intent**:
The kind of situation a Comment presents, which decides which Canned replies are eligible for it.
_Avoid_: category, topic, class, label

**Normalization**:
The step that rewrites a Comment's text into a canonical form for matching, leaving the Comment as stored untouched.
_Avoid_: cleaning, preprocessing, canonicalisation, stemming

**Tail**:
A Comment that no Canned reply covers, and which therefore needs one written for it.
_Avoid_: miscellaneous comment, edge case, fallback

**Router**:
The step that assigns each Comment either a Canned reply or the Tail.
_Avoid_: classifier, matcher

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
The maximum number of Replies one Platform agent may post in a day. The count survives a restart, so restarting the agent cannot buy more Replies.
_Avoid_: rate limit, throttle, budget

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
