# Comment identity across TikTok, Facebook and Instagram

How each Platform exposes a per-Comment identifier in the DOM, and why the Replied set keys
on it.

**How this was gathered.** No logged-in session was used. TikTok serves a captcha to
unauthenticated requests, Instagram's embed returns a login splash, Facebook's desktop page is
a JavaScript shell with no server-rendered Comments, and the Wayback Machine was unavailable
throughout. Everything below therefore rests on captured page HTML published in public
repositories, the source of working tools, and engineering notes carrying verification dates.
Real captured HTML is the strongest of those, and only TikTok and Instagram have it.

**Read this before trusting it.** These findings are good enough to design against and not
good enough to rely on. They are other people's Recorded pages, taken at unknown dates
against builds that have since moved. Confirming them against the user's own logged-in pages
is exactly the job of this project's own Recorded pages, and it should happen before any
Adapter is written against them.

## Instagram

The cleanest of the three. Each Comment's permalink anchor wraps its timestamp:

```html
<a href="/p/DckwEXmCPFu/c/17902321296556350/" role="link">
  <time datetime="2026-08-28T06:47:31.000Z">
```

- The `17902321296556350` is the Comment `pk`, the same identifier the Graph API reports. It
  is stable across page loads and sessions.
- **Reply parentage is in the URL.** A reply's permalink is
  `/p/{shortcode}/c/{parentId}/r/{replyId}/`, so the path yields both the reply's own
  identifier and its parent's without inferring anything from DOM nesting.
- Timestamps are absolute ISO-8601 UTC, the only Platform of the three that gives this.
- Comment elements carry no `id` and no useful `data-*` attributes. Permalink presence is
  the reliable "is this a Comment" test, since the caption row also lacks one.

Sources: [real captured IG comment HTML](https://github.com/siavashh/xtract-replies/blob/HEAD/instagram.html) ·
[DOM extraction rules](https://github.com/siavashh/xtract-replies/blob/HEAD/.cursor/rules/instagram-dom-extraction.mdc) ·
[selector constants](https://github.com/calumba-holding/cyberheld-apify-facebook-scraper/blob/HEAD/src/instagram/selectors.ts) ·
[native_comments.py](https://github.com/jsonifyco/instagram-scraper/blob/HEAD/src/instagram_scraper/ig/native_comments.py) ·
[permalink adapter](https://github.com/Hao0321/claude-skill-social-post/blob/HEAD/social-post/scripts/comment_chrome_instagram_reader.mjs)

## TikTok

**TikTok puts no Comment identifier in the DOM at all.** This is the counter-intuitive
result, because `data-e2e` attributes are what everyone cites for TikTok selectors, and they
are genuinely useless for identity. From a real 244 KB captured comment panel:

- `data-e2e="comment-level-1"`, `comment-username-1` and `comment-reply-1` each appear on
  every top-level Comment. They name the parts of a Comment, not one Comment.
- There is no `data-comment-id`, no `data-cid`, and no per-Comment `id`.
- The only `id` attributes present are an SVG gradient id duplicated 21 times, and the
  composer's editor id, which is random per render. **Any `#id` selector on TikTok is unsafe**,
  because a duplicated id makes the selector silently match the wrong node.
- Timestamps render as relative text (`"3d ago"`). The capture contains zero `<time>` elements
  and zero `datetime` attributes, so no absolute time is available in the DOM.

The real identifier lives in React props on the Comment node. The prop key (`__reactProps$…`)
is per-render, but is discovered at runtime, and the `cid` inside it is the Platform's stable
global Comment id:

```js
const key = Object.getOwnPropertyNames(li).find(k => k.startsWith('__reactProps$'))
const cid = li[key]?.children?.props?.item?.comment?.comment?.cid
```

The same object carries `create_time` as absolute unix seconds, `reply_id` (`"0"` for
top-level, the parent's `cid` for a reply), `reply_to_reply_id`, and `user.uid`.

**The consequence that matters most: `cid` is durable but not addressable.** It cannot be used
to find the Comment on the page. Every working implementation re-finds the target by author
handle plus body text and then re-reads the React props to confirm the `cid` matches before
acting. Identity and addressability are separate problems here, and only one of them is
solved by having the id.

Class names rotate on deploy, and TikTok has changed its naming scheme (a `-7937d88b--` build
segment is new), so only the semantic middle token survives:

- observed now: `css-7waxo-7937d88b--DivCommentItemWrapper`
- previously: `css-1i7ohvi-DivCommentItemContainer`, `css-9uczur-DivCommentItemContainer`

Top-level versus reply is best read structurally: a top-level Comment is a
`[class*="DivCommentObjectWrapper"]` and a reply is not, while replies sit inside
`[class*="DivReplyContainer"]`. The `data-e2e` suffix (`-1` top-level, `-2` reply) corroborates
it. Authoritative parentage still comes from React props.

Sources: [real captured TikTok HTML](https://github.com/gigamesh/tokative/blob/HEAD/html-snippets/tiktok-post-comments.html) ·
[extract-react-props.ts](https://github.com/gigamesh/tokative/blob/HEAD/apps/extension/src/content/tiktok/extract-react-props.ts) ·
[video-scraper.ts](https://github.com/gigamesh/tokative/blob/HEAD/apps/extension/src/content/tiktok/video-scraper.ts) ·
[comment-replier.ts](https://github.com/gigamesh/tokative/blob/HEAD/apps/extension/src/content/tiktok/comment-replier.ts) ·
[locators.py](https://github.com/strymsg/wayrunku-desinformacion-politica/blob/HEAD/src/tiktok/scraper/locators.py) ·
[fetch-tiktok-comments.js](https://github.com/Hazy019/social-ai-responder/blob/HEAD/api/fetch-tiktok-comments.js) ·
[tiktok-ai-reply-bot](https://github.com/WetHemBoys755/tiktok-ai-reply-bot/blob/HEAD/server.js)

## Facebook

The identifier is a query parameter on the Comment's timestamp anchor:
`a[href*="comment_id="]` for a top-level Comment, `reply_comment_id=` for a reply.

**It is best-effort, not guaranteed.** One implementation that measured it reports that
permalink and modal layouts frequently do not render the target `comment_id` as an anchor at
all, with the Comment still present and correctly labelled. No source quantified how often,
so treat "always present" as unproven.

Comment containers are `[role="article"]`, which accessibility requirements keep stable across
years, and their `aria-label` distinguishes the two levels:

- top-level: `aria-label="Comment by {Name} …"`
- reply: `aria-label="Reply by {Owner} to {X}'s comment"`

Both labels are **localised**, so a selector keyed on the English strings breaks on a
non-English interface, and the reply label is not applied reliably. Facebook nests replies
inside their parent article, so ancestor `[role="article"]` depth is the corroborating signal.

No absolute Comment timestamp was found in current markup. The Comment timestamp renders
relative text.

Every implementation surveyed carries a content-hash fallback when the anchor is missing, and
one documents the consequence precisely: a text-based key changes when the text is edited, so
**an edited Comment looks like a new one and receives a second Reply**. That is the largest
correctness risk to the never-reply-twice guarantee anywhere in this project.

Sources: [facebook_public_scraper.py](https://github.com/HaTranThai/Social-Listening/blob/HEAD/facebook/app/scrape/facebook_public_scraper.py) ·
[enrich_comment_parents.py](https://github.com/vyakunin/homebound/blob/HEAD/tools/fb_activity_log_extension/automation/enrich_comment_parents.py) ·
[crawler-social facebook.md](https://github.com/tu-hm/crawler-social/blob/HEAD/docs/sources/facebook.md) ·
[FB Comments Exporter](https://github.com/disrex-group/FB-Comments-Exporter-User-script/blob/HEAD/facebook-comment-scraper.user.js) ·
[comment_cic.py](https://github.com/hoangzip/ai-agent/blob/HEAD/crawl_facebook_1/facebook-group-collector/collector/facebook/comment_cic.py) ·
[html2vec facebook.js](https://github.com/jawerty/html2vec/blob/HEAD/crawlers/scrapers/facebook.js) ·
[Faceberg notes](https://github.com/justgitgut/Faceberg/blob/HEAD/docs/comment-automation-notes.md) ·
[fb-dom-strategy.md](https://github.com/NolanFox/rhodesli/blob/HEAD/docs/session_context/session-159-research/03-fb-dom-strategy.md)

## What this means for the Replied set

The key is per-Platform, because the Platforms do not agree on what a Comment is:

| Platform | Key | Available |
|---|---|---|
| Instagram | `ig:{shortcode}:{commentId}` | Always, from the permalink |
| TikTok | `tt:{awemeId}:{cid}` | Always, from React props |
| Facebook | `fb:{commentId}` | Often, from the timestamp anchor |

Three things follow.

1. **Never key on a content hash where a real identifier exists.** On Facebook, where the
   real identifier is sometimes absent, a hash fallback means an edited Comment is answered
   twice. Skipping an unidentifiable Comment costs one unanswered Comment; guessing costs a
   visible duplicate Reply.
2. **Identity is not addressability.** Holding a `cid` on TikTok does not let the agent find
   the Comment to reply to it. The write path has to re-find by author and text and then
   re-verify the id it reads against the id it holds. That verification is what makes a
   double Reply structurally detectable rather than merely unlikely, and it doubles as the
   Confirmation step that Reconciliation needs.
3. **Selectors must not live in released code.** TikTok changed its class-name scheme within
   the lifetime of the tools inspected. The one implementation that survives this keeps its
   selectors in a remote configuration updatable without a release.

## What could not be determined

- No logged-in observation of any Platform. This is the standing limitation of the whole
  document.
- How often Facebook's `comment_id` anchor is actually absent, as opposed to known-absent.
- Whether Facebook exposes an absolute Comment timestamp anywhere in current markup.
- Instagram's modal Comment layout, which the captured fixture does not cover.
- Whether TikTok's `data-e2e="comment-item"` is historical or surface-specific. It is cited by
  several scrapers and absent from the build inspected.
- A trap worth carrying forward: `data-e2e="comment-level-1"` means the Comment text span in
  the video panel but the whole row in the notification inbox. One selector string, two
  meanings, so selectors are not portable between surfaces.
