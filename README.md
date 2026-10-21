# social-reply-agent

A fully automated comment-section replying agent for multiple social platforms.

**Built on browser automation, with no official platform APIs.** That is a
deliberate constraint, and it shapes everything below.

Status: **design stage.** The auth layer is built and tested; the agent itself
is not written yet.

## The constraint, and what it costs

Without APIs, the logged-in browser session *is* the credential — there is no
token to rotate. Two consequences follow, and they are the two things this
project has to get right:

1. **Session persistence is the auth layer.** If it breaks, everything breaks,
   and it breaks *silently* — the agent simply acts logged out.
2. **Selector rot is the primary risk.** The dangerous failure is not a crash.
   It is a locator that still matches, but now matches the **wrong element** —
   which in a reply bot means replying to the wrong person.

## What's here

| File | Purpose |
| --- | --- |
| `pw_session.py` | The auth layer: durable profile + cookie jar per account |
| `login.py` | Open an account's profile visibly so you can log in by hand |
| `test_persistence.py` | Proves the login survives between runs |

## The one non-obvious thing

`pw_session.py` keeps **both** a browser profile and a cookie jar, and the
redundancy is load-bearing:

| State | Survives via profile? |
| --- | --- |
| localStorage / IndexedDB / service workers | **Yes** |
| Cookies | **No** |

Under Playwright, Chromium never flushes its cookie SQLite store on the way
out — not on `ctx.close()`, not on `browser.close()`. So the obvious "just
point it at a `user-data-dir`" design logs you out every run while looking like
it works. `pw_session.py` therefore layers `storage_state` on top of the
profile: replayed with `ctx.add_cookies()` on open, written back on close.

Note that `launch_persistent_context()` takes **no** `storage_state` argument —
passing one raises `TypeError`. Don't try to collapse the two steps.

## Running

```bash
uv venv .venv --python python3
uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/python -m playwright install chromium

.venv/bin/python -m pytest
.venv/bin/python login.py instagram https://www.instagram.com/   # log in once
```

Profiles live in `~/.config/social-bot/accounts/<account>/`; cookie jars in
`~/.config/social-bot/state/<account>.json`, mode `0600` and gitignored — they
hold live session credentials.

**When an adapter starts acting logged out, re-run `login.py` first.** That is
the overwhelmingly likely cause and it is free to check.

## Related

`~/selenium-scratch` is the experiment bench: the older Selenium setup, the
pinned-driver notes, and the Playwright environment write-up live there. It is
deliberately not part of this repo.
