#!/usr/bin/env python
"""Operator-run tool: save a TikTok page for Recorded-page development.

This tool is for a human operator using a logged-in Session. It is not part of
adapter reads or tests, and nothing should import it.

A capture is only useful if the Comments are in it. The Recorded-page adapter
reads Comment nodes out of the saved DOM, so a page saved before the Comment
panel has rendered has nothing to read and the capture is wasted. Rather than
guess at the Platform's UI, this tool waits a bounded time for the panel, and
where it does not appear it leaves the browser open and asks the operator to
open it -- or, when there is no terminal to ask through, waits for the panel to
appear. It then checks what it actually captured and says so, so a useless
capture is obvious in this run rather than in the next one.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

# Run as `python3 tools/capture_page.py` from anywhere: the Session helper lives at
# the repository root, and the script's own directory is what lands on `sys.path`.
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from playwright.sync_api import TimeoutError as PlaywrightTimeout

from pw_session import session

# Kept in step with `agent/adapters/tiktok.py` by hand. This tool must not import
# the adapter, and the adapter must not depend on this tool.
_COMMENT_PANEL_SELECTOR = '[data-e2e="comment-level-1"]'
_COMMENT_LIST_ITEM_SELECTOR = '[data-e2e="comment-level-1"] > *'
_COMMENT_ID_ATTR = 'data-comment-id'
_COMMENT_TEXT_SELECTOR = '[data-e2e="comment-text"]'
_TOTAL_SELECTOR = '[data-e2e="comment-count"]'
_STATE_SCRIPT_SELECTOR = 'script[id="__UNIVERSAL_DATA_FOR_REHYDRATION__"]'

_PANEL_WAIT_MS = 30_000
_SETTLE_MS = 2_000
# After the bounded wait fails we hand over to the operator: where stdin is a
# terminal they press Enter once the panel is open. Where it is not -- a command
# run through a harness, say -- there is nothing to press, and carrying straight
# on would save a page with no Comments in it, which is the one outcome this
# whole check exists to prevent. So poll for the panel instead.
_OPERATOR_POLL_MS = 5_000
_OPERATOR_DEADLINE_S = 300


def _wait_for_operator(page) -> None:
    """Give the operator a chance to open the Comments before we save the page."""
    print(
        f"The Comment panel is not in the page after {_PANEL_WAIT_MS // 1000}s. "
        "In the browser window, open the Comments and scroll until they are "
        "visible, then press Enter here to capture."
    )
    try:
        input()
        return
    except EOFError:
        pass

    print(
        "No interactive stdin, so the Enter prompt is unavailable. Waiting up to "
        f"{_OPERATOR_DEADLINE_S // 60} minutes for the Comment panel to appear."
    )
    deadline = time.monotonic() + _OPERATOR_DEADLINE_S
    while time.monotonic() < deadline:
        page.wait_for_timeout(_OPERATOR_POLL_MS)
        if page.locator(_COMMENT_PANEL_SELECTOR).count():
            print("Comment panel found; capturing.")
            return
        print(f"  still waiting for the Comment panel (~{int(deadline - time.monotonic())}s left)")
    print("Gave up waiting for the Comment panel; capturing what is on the page.")


def _summarise(page) -> dict:
    """What the adapter will be able to read from what we are about to save."""
    items = page.locator(_COMMENT_LIST_ITEM_SELECTOR)
    identified = 0
    for index in range(items.count()):
        if (items.nth(index).get_attribute(_COMMENT_ID_ATTR) or "").strip():
            identified += 1

    total_locator = page.locator(_TOTAL_SELECTOR)
    return {
        "state_script_present": page.locator(_STATE_SCRIPT_SELECTOR).count() == 1,
        "comment_panel_count": page.locator(_COMMENT_PANEL_SELECTOR).count(),
        "comment_items": items.count(),
        "comment_items_with_identifier": identified,
        "comment_text_nodes": page.locator(_COMMENT_TEXT_SELECTOR).count(),
        "comment_count_label": (
            (total_locator.first.text_content() or "").strip() if total_locator.count() else None
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Operator-run capture tool. Requires a logged-in Session and a visible browser."
    )
    parser.add_argument("account", help="Account name whose Session is already logged in")
    parser.add_argument("url", help="TikTok Post URL to capture")
    parser.add_argument("path", help="Destination HTML path")
    args = parser.parse_args()

    destination = Path(args.path).expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)

    with session(args.account, headless=False) as ctx:
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(args.url, wait_until="domcontentloaded")
        try:
            page.wait_for_selector(_COMMENT_PANEL_SELECTOR, timeout=_PANEL_WAIT_MS)
        except PlaywrightTimeout:
            _wait_for_operator(page)
        page.wait_for_timeout(_SETTLE_MS)

        summary = _summarise(page)
        destination.write_text(page.content(), encoding="utf-8")

        sidecar = destination.with_suffix(destination.suffix + ".capture.json")
        sidecar.write_text(
            json.dumps(
                {
                    "url": args.url,
                    "account": args.account,
                    "captured_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                    "page": str(destination),
                    **summary,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    print(f"saved Recorded page to {destination}")
    print(f"saved capture summary to {sidecar}")
    print(json.dumps(summary, indent=2))
    if summary["comment_items_with_identifier"] == 0:
        print(
            "WARNING: no Comment in this capture carried an identifier, so the adapter "
            "cannot read it. Re-run with the Comment panel open and populated."
        )
    if not summary["state_script_present"] and summary["comment_count_label"] is None:
        print(
            "WARNING: this capture has neither the rehydration state script nor a total "
            "label, so the adapter cannot check completeness on it."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
