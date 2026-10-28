# Capturing a Recorded page from the live Platform

A Recorded page is a real page saved by hand and replayed offline in tests. It is the only
way this project learns what a Platform's markup actually is; every fixture written before
one exists is synthetic and proves only that a reader agrees with itself.

This is an **operator step**. It needs a human, a visible browser, and (for TikTok) a
logged-in Session. It is not part of the test suite and nothing imports
`tools/capture_page.py`.

## What the tool does, and why it is shaped that way

1. **Discovers Comment nodes instead of asserting a selector.** It counts
   `[class*="DivCommentItem"]`, `[class*="DivCommentObjectWrapper"]`,
   `[data-e2e="comment-item"]` and a set of corroborating selectors, and uses the first one
   that matches. A capture tool that waits on one hard-coded selector fails by timing out
   and saving an empty panel, which is the failure this whole step exists to prevent.
2. **Records the page's own `comment/list` responses.** TikTok puts no Comment identifier in
   the DOM; the `cid` is in the JSON its web client fetches. The tool observes that request
   and never makes one itself — observing is browser automation, calling the endpoint by
   hand is not (ADR 0001).
3. **Scrolls to defeat lazy loading.** Reading the first page and calling it the section is
   the measured failure mode (20 read against `total: 569`). The tool drives the panel's own
   scroll container for up to three minutes.
4. **States its own completeness.** `total` from the API is compared against the number of
   distinct `cid`s seen. `has_more: 0` is not treated as evidence.

## The run

From the main checkout, on `master`, with the project venv:

```bash
git pull
.venv/bin/python login.py tiktok https://www.tiktok.com/     # once; close the window when logged in
.venv/bin/python tools/capture_page.py tiktok '<post-url>'
```

The second command writes, under `data/captures/` (git-ignored):

| file | contents |
|---|---|
| `tiktok-<post>-<stamp>.html` | the saved DOM |
| `…html.capture.json` | selector counts, Comment counts, cid count, `total`, completeness, warnings |
| `…html.comment-list.json` | the raw `comment/list` responses — the only place `cid` exists |

Pass a path to override the default. The tool **refuses** to write anywhere inside the repo
that git does not ignore, because a capture carries third parties' Comment text and handles.

**By hand:** the browser opens headed. Comments render only in a headed browser on TikTok,
so do not be tempted to run this headless. If no Comment node matches within 30 seconds, the
tool asks you in the terminal to open the Comments and press Enter. After that it scrolls on
its own; leave it until it prints the summary.

**Pick the Post deliberately.** One already in `docs/labelled-set-tiktok.md` lets the capture
be checked against rows we have read before. A Post with tens of Comments, not hundreds, is
easier to eyeball.

## Reading the result

The sidecar's last lines are the verdict:

- `"completeness": "complete"` — distinct `cid`s reached the API's `total`. This is the only
  claim that the capture holds the whole section.
- `"truncated"` — the API reported more than was seen. The gap is a finding, not a bug in the
  run: record both numbers.
- `"unknown"` — no `comment/list` response was observed. The capture cannot speak about
  completeness at all.

Every `WARNING:` line is a reason the capture would have been a wasted trip, printed in the
run that produced it rather than in the next one.

## What happens next

The capture is reconciled against `agent/adapters/tiktok.py`. Two outcomes are possible and
both are results:

- the Adapter's shape survives contact, and its selectors and identifier source are updated
  to the measured ones;
- it does not, and the discrepancy goes into the Adapter's docstring and ADR 0019's bar 4,
  because that bar cannot be discharged by a reader that was written from imagination.

Only after that does the question of a committed fixture arise: the capture itself stays in
`data/`; a fixture derived from it must first be scrubbed to invented text (the corpus is
public, but a fixture is not the same decision as a corpus row).
