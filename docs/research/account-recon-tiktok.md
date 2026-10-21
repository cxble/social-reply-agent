# Account recon: @benooicb on TikTok

Reconnaissance for the Reply table, run 2026-10-21. **No logged-in Session was used** — every
finding below is from a logged-out browser. The distinction that turned out to matter was not
logged-in versus logged-out but **headed versus headless**, and an earlier revision of this
document got that wrong. See "The headless result was an artifact" below.

## The Account

| | |
|---|---|
| Display name | Bro Ben Ooi |
| Handle | @benooicb |
| Followers | 91.7K |
| Following | 1,195 |
| Likes | 249.6K |
| Bio | Pertubuhan Kebajikan dan Pembangunan Insan Pulau Pinang. |

The Account belongs to a Penang welfare organisation — by its own account of events, founded at the end of 2025 and registered with ROS in January 2026. The posts are Malay-language and Islamic-framed.

## What the posts are about

Captions, read logged-out, from four sampled posts:

- **Ziarah 1/100 — Sungai Ara, Pulau Pinang.** Visiting a teacher in a coma, framed around Surah Al-Mumtahanah and the Prophet's ﷺ visiting a sick non-Muslim, closing with an invitation to join in doa. 26 Comments, 130 Likes.
- **The organisation's founding story**, covering "Ziarah 100 Keluarga" and "Projek Rumah Kak Dewi". **2,712 Comments, 21.5K Likes.**
- **A conversion post** — a man from Kelantan who accepted Islam in Penang, framed around Surah Al-Qasas 56. **569 Comments, 1,685 Likes.**
- A photo post, which rendered nothing logged-out.

Comment counts on the sample run 26 / 569 / 2,712. The busy posts carry hundreds to low thousands of Comments each, which is the volume the design has to survive rather than the cap.

## What is visible without a Session

Verified by driving a real headless Chromium, and by the public oEmbed and embed endpoints:

| Surface | Logged out, headless | Logged out, headed |
|---|---|---|
| Profile header — name, handle, counts, bio | visible | visible |
| Video grid on the profile | **not visible.** Slider CAPTCHA; zero video links in the DOM | not re-tested |
| Caption and like/comment/share counts on a post page | visible | visible |
| Comment list on a post page | **not visible. Zero comment nodes** | **visible. 40 nodes, all with text** |
| Posting a Comment | not possible — "Log in to comment" | not possible — "Log in to comment" |
| oEmbed (`/oembed?url=…`) | iframe HTML only — no title, author or caption | same |
| Embed page (`/embed/v2/<id>`) | 312 KB of rehydration JSON exposing `commentCount` and **no comment text** | same |

**Reading Comments does not require a Session; posting does.** The video grid on the profile
stays CAPTCHA-gated either way, so the way in is a Post URL, not the profile.

**And the panel opens on the wrong tab.** The comment panel has two tabs, `Comments` and
`You may like`, and it opens on `You may like` — whose tiles are skeletons. A read that does not
select the Comments tab first returns zero Comments on every Post, headed or not, with the real
count rendered on the page beside it. Select the tab, then check the count before believing an
empty list. ADR 0013 carries this.

## The headless result was an artifact

An earlier revision of this document concluded, from a zero, that no Comment text was
obtainable without a Session. That conclusion was wrong, and wrong in a shape worth recording.

Every one of those runs launched Chromium **headless**. Headless TikTok renders the comment
panel — the container, the counters, the composer — but leaves every row as a grey skeleton
placeholder, so the DOM contains the panel and not one Comment. The count was real; the
inference drawn from it was not.

The same page in a **headed** browser, still logged out, returned 40 Comment nodes with 40
non-empty bodies on the first read, and the same again on a second read after scrolling.

The relevant detail is the selector, because it is the thing that made the zero look
trustworthy. The probe asked for `[data-e2e^="comment-level"]` — a selector taken from
`comment-identity.md`, which was itself written without a live page. On the living DOM that
selector matches **nothing**, logged in or out:

```
DivCommentItem: 10   CommentItem: 10   CommentList: 1   comment-level: 0
```

So two faults compounded: a selector that never matches, queried in a mode that returns
nothing to match. Either alone would have produced the same `0`, and neither would have been
visible in the result.

**The engineering consequence is larger than the recon correction.** A headless Platform
agent does not fail here. It reads an empty Comment list on every Post, finds nothing eligible,
and reports a clean pass. Nothing raises, no page errors, the Session is alive — the agent
looks healthy while doing absolutely nothing, and the Daily cap never fills because there is
never anything to reply to. A silent-empty read is indistinguishable from a quiet comment
section, and this Platform produces it by default.

What follows for the design: **the read path must not run headless**, and an empty Comment
list from a Post whose page reports a non-zero `commentCount` is a **failure, not an empty
result**. The count is available on the same page that withheld the Comments — the embed
endpoint and the post page both expose it — so this is checkable rather than a matter of care.
That check belongs in the Adapter as a first-class outcome, not in a log line.

## What this means for the Reply table

The table **must not be guessed at.** `GLOSSARY.md` says Variants "are added only from real
Comments, never guessed", and this is the case that rule exists for. What changed is that real
Comments are now reachable, so the table can be built from them rather than deferred.

What the captions establish is the shape of the Intent set the table will need — and one hazard:

- **Doa and blessing Comments.** Expected to dominate on a welfare organisation's posts.
- **Donation enquiries** — how to contribute, the organisation's account details, zakat and sedekah.
- **Volunteer offers.**
- **Help requests** — people asking the organisation to assist them or their family.

**The last one is the hazard, and it should be decided before the table is populated rather than after.** A welfare organisation's comment section is where people in difficulty ask for help in public. A Canned reply is the wrong answer to a plea for assistance no matter how well it matches, so that category needs an Intent that routes to Escalation rather than into the table. This is a content decision that shapes the schema, not a later tuning pass.

## Still to collect

- Comment text per post, across the tracked posts — in progress, see above.
- Comment identity in the shapes recorded in `comment-identity.md`, **re-verified against the
  living DOM**. That document carries the same no-live-page caveat as this one, and its TikTok
  selector is already known to be wrong; the working one is `[class*="DivCommentItem"]`.
- The actual Variant spellings, which is the part that cannot be reasoned about from outside.
- Whether the headed requirement is specific to TikTok or general across Platforms. It is
  unmeasured on Facebook and Instagram, and it changes the deployment shape — a headed browser
  needs a display, which this machine has and a container usually does not.
