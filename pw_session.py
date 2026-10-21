"""Playwright driving a durable Chromium profile, plus an explicit cookie jar.

With no official APIs in play, the logged-in session *is* the auth layer for
every platform, so it has to survive between runs. That takes two mechanisms,
because one is not enough:

* a persistent ``user-data-dir`` per account, carrying localStorage, IndexedDB
  and service-worker state; and
* a ``storage_state`` JSON per account, carrying **cookies**.

The second is not redundant. Under Playwright, Chromium does not flush its
cookie SQLite store on the way out — not even on a graceful ``browser.close()``
— so a profile-only setup logs you out every single run while appearing to
work. Verified on Playwright 1.64 / Chrome for Testing 156: localStorage
survived the profile, cookies did not, and this jar fixed it. See the README
before deleting it.
"""

import json
from contextlib import contextmanager
from pathlib import Path

from playwright.sync_api import sync_playwright

CONFIG_ROOT = Path.home() / ".config" / "social-bot"
PROFILE_ROOT = CONFIG_ROOT / "accounts"
STATE_ROOT = CONFIG_ROOT / "state"

# Playwright launches Chromium with --enable-automation, which shows the
# "controlled by automated software" banner and sets navigator.webdriver. This
# drops both. It is not a stealth kit: sites also key on behavioural signals
# (timing, velocity), IP reputation and account history, none of which a launch
# flag can touch. See the README for what that means for pacing.
LAUNCH_ARGS = ["--disable-blink-features=AutomationControlled"]


def _system_timezone() -> str:
    """The host's tz name, so the browser doesn't report UTC from Malaysia."""
    link = Path("/etc/localtime")
    if link.is_symlink():
        target = str(link.resolve())
        if "/zoneinfo/" in target:
            return target.split("/zoneinfo/", 1)[1]
    return "UTC"


def profile_dir(account: str) -> Path:
    """Where an account's browser profile lives, created on demand."""
    path = PROFILE_ROOT / account
    path.mkdir(parents=True, exist_ok=True)
    return path


def state_path(account: str) -> Path:
    """Where that account's saved cookies live. Sensitive — kept 0600."""
    STATE_ROOT.mkdir(parents=True, exist_ok=True)
    return STATE_ROOT / f"{account}.json"


def _restore(context, path: Path) -> None:
    """Load saved cookies (and localStorage) into a fresh context."""
    if not path.exists():
        return
    try:
        state = json.loads(path.read_text())
    except (OSError, ValueError):
        return  # a corrupt jar means a re-login, not a crash

    if state.get("cookies"):
        context.add_cookies(state["cookies"])

    # The profile already carries localStorage; replaying it from the jar keeps
    # the state file a complete, portable backup of the login.
    for origin in state.get("origins") or []:
        items = origin.get("localStorage") or []
        if not items:
            continue
        body = "".join(
            f"localStorage.setItem({json.dumps(i['name'])}, {json.dumps(i['value'])});"
            for i in items
        )
        context.add_init_script(
            f"if (location.origin === {json.dumps(origin['origin'])}) {{ {body} }}"
        )


def _save(context, path: Path) -> None:
    context.storage_state(path=str(path))
    path.chmod(0o600)


@contextmanager
def session(account: str, headless: bool = True, save: bool = True, **overrides):
    """Yield a BrowserContext carrying `account`'s profile and cookie jar.

    Anything Playwright accepts on launch_persistent_context can be overridden
    per call — e.g. ``slow_mo=250`` while debugging a recorded flow.
    """
    options = {
        "user_data_dir": str(profile_dir(account)),
        "headless": headless,
        "args": LAUNCH_ARGS,
        "viewport": {"width": 1280, "height": 900},
        "timezone_id": _system_timezone(),
        "locale": "en-US",
    }
    options.update(overrides)

    # launch_persistent_context has no storage_state parameter, so the jar goes
    # in via add_cookies() instead.
    jar = state_path(account)
    with sync_playwright() as pw:
        context = pw.chromium.launch_persistent_context(**options)
        try:
            _restore(context, jar)
            yield context
        finally:
            if save:
                try:
                    _save(context, jar)
                except Exception:
                    pass  # best-effort; never mask the caller's own error
            context.close()
