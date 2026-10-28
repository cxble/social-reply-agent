#!/usr/bin/env python
"""Operator-run tool: save a TikTok page for Recorded-page development.

This tool is for a human operator using a logged-in Session. It is not part of
adapter reads or tests, and nothing should import it.

**It discovers, it does not assert.** `docs/research/comment-identity.md` found
that the selectors this tool used to wait on match no node on the live page:
`[data-e2e^="comment-level"]` reads zero where `[class*="DivCommentItem"]` reads
every Comment, and `data-e2e="comment-level-1"` is the Comment *text* span. A
capture tool built on the wrong selector does not fail loudly; it times out,
saves an empty panel, and calls it a capture. So this tool counts a list of
candidate selectors, treats the first one that matches as the Comment node set,
and reports every candidate in its sidecar. When the next rename happens the
sidecar says which selector stopped working, which is the information the next
person needs.

**The identifier is not in the DOM.** TikTok's web client fetches Comments from
`/api/comment/list/`, and that JSON carries `cid` per Comment plus `total`,
`has_more` and `cursor`. The tool records those responses as the page makes
them -- it never calls the endpoint itself, because a hand-driven request is not
browser automation (ADR 0001). `total` is the only trustworthy completeness
signal: `has_more: 0` is not evidence that the section has been read.

**It scrolls.** Comments lazy-load, and reading the first page while reporting
it as the section is the failure the research doc measured (20 read against
`total: 569`). The tool drives the panel's own scroll container, bounded by a
deadline, and reports what it saw against the API's `total`.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

# Run as `python3 tools/capture_page.py` from anywhere: the Session helper lives at
# the repository root, and the script's own directory is what lands on `sys.path`.
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from playwright.sync_api import TimeoutError as PlaywrightTimeout  # noqa: E402

from pw_session import session  # noqa: E402

# Candidate selectors, most-likely first. The research doc's correction of
# 2026-10-21 named `DivCommentItem` as the working one; the rest are history or
# corroboration. All are *counted*; the first with a non-zero count defines the
# Comment set for the summary.
COMMENT_NODE_CANDIDATES = (
    '[class*="DivCommentItem"]',
    '[class*="DivCommentObjectWrapper"]',
    '[data-e2e="comment-item"]',
)
# Counted but never used as the Comment set: on the video panel this is the text
# span inside a Comment, not a Comment container.
CORROBORATING_SELECTORS = (
    '[data-e2e^="comment-level"]',
    '[data-e2e="comment-level-1"]',
    '[data-e2e="comment-username-1"]',
    '[data-e2e="comment-reply-1"]',
    '[class*="DivReplyContainer"]',
    '[class*="DivCommentListContainer"]',
)
COMMENT_TEXT_SELECTOR = '[data-e2e="comment-level-1"]'
COMMENT_AUTHOR_SELECTOR = '[data-e2e="comment-username-1"]'
_STATE_SCRIPT_SELECTOR = 'script[id="__UNIVERSAL_DATA_FOR_REHYDRATION__"]'

_COMMENT_LIST_MARKER = "/api/comment/list"
_PANEL_WAIT_MS = 30_000
_SETTLE_MS = 2_000
# After the bounded wait fails we hand over to the operator: where stdin is a
# terminal they press Enter once the panel is open. Where it is not -- a command
# run through a harness, say -- there is nothing to press, and carrying straight
# on would save a page with no Comments in it, which is the one outcome this
# whole check exists to prevent. So poll for the panel instead.
_OPERATOR_POLL_MS = 5_000
_OPERATOR_DEADLINE_S = 300
# Lazy-loading: stop when node count and API page count have both been stable
# for this many consecutive polls, or when the deadline passes.
_SCROLL_POLL_MS = 1_500
_SCROLL_STABLE_POLLS = 3
_SCROLL_DEADLINE_S = 180

_SCROLL_TO_END_JS = """
() => {
  const candidate = document.querySelector('[class*="DivCommentItem"]')
    || document.querySelector('[class*="DivCommentObjectWrapper"]')
    || document.querySelector('[data-e2e="comment-item"]');
  if (candidate) {
    let node = candidate;
    while (node && node !== document.body) {
      const style = getComputedStyle(node);
      if (/(auto|scroll)/.test(style.overflowY) && node.scrollHeight > node.clientHeight + 5) {
        node.scrollTop = node.scrollHeight;
        return {scroller: "ancestor", scroll_height: node.scrollHeight};
      }
      node = node.parentElement;
    }
  }
  window.scrollTo(0, document.body.scrollHeight);
  return {scroller: "window", scroll_height: document.body.scrollHeight};
}
"""


# --- the page's own comment/list responses -----------------------------------


def parse_comment_list(payload: Any) -> dict:
    """Pull the fields this tool reports out of one comment/list response.

    The shape is `{comments: [...], cursor, has_more, total}`; some builds nest
    it under `data`. Anything else yields an empty record rather than a guess.
    """
    node = payload
    if isinstance(node, dict) and isinstance(node.get("data"), dict):
        node = node["data"]
    if not isinstance(node, dict):
        return {"comments": 0, "cids": [], "total": None, "has_more": None, "cursor": None}

    comments = node.get("comments")
    cids: list[str] = []
    if isinstance(comments, list):
        for comment in comments:
            if isinstance(comment, dict) and comment.get("cid") is not None:
                cids.append(str(comment["cid"]))
    return {
        "comments": len(comments) if isinstance(comments, list) else 0,
        "cids": cids,
        "total": _as_int(node.get("total")),
        "has_more": _as_int(node.get("has_more")),
        "cursor": _as_int(node.get("cursor")),
    }


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and re.fullmatch(r"\d+", value.strip()):
        return int(value.strip())
    return None


def is_comment_list_response(url: str) -> bool:
    """True for the page's own top-level Comments request, and nothing else.

    `/api/comment/list/reply/` is a different request whose `total` counts
    replies, so letting it through would corrupt the completeness check.
    """
    path = urlsplit(url).path
    return path.rstrip("/").endswith(_COMMENT_LIST_MARKER)


def read_comment_list_response(response) -> dict | None:
    """Parse a stored Playwright response, tolerating a non-JSON body."""
    if not is_comment_list_response(response.url):
        return None
    try:
        payload = response.json()
    except Exception:  # a body may be gone, HTML, or an error page
        try:
            payload = json.loads(response.text())
        except Exception:
            return None
    record = parse_comment_list(payload)
    record["url"] = response.url
    record["status"] = response.status
    return record


# --- page probing -------------------------------------------------------------


def _count(page, selector: str) -> int:
    try:
        return page.locator(selector).count()
    except Exception:
        return 0


def count_selectors(page) -> dict:
    """Every candidate's count, so a rename shows up as a zero next to a non-zero."""
    return {
        selector: _count(page, selector)
        for selector in COMMENT_NODE_CANDIDATES + CORROBORATING_SELECTORS
    }


def _comment_nodes(page):
    """The first candidate selector that matches anything."""
    for selector in COMMENT_NODE_CANDIDATES:
        locator = page.locator(selector)
        if locator.count():
            return selector, locator
    return None, None


def _text_and_author(node) -> tuple[str, str]:
    text_locator = node.locator(COMMENT_TEXT_SELECTOR)
    if text_locator.count():
        text = (text_locator.first.text_content() or "").strip()
    else:
        text = (node.inner_text() or "").strip()
    author_locator = node.locator(COMMENT_AUTHOR_SELECTOR)
    author = (author_locator.first.text_content() or "").strip() if author_locator.count() else ""
    return text, author


def _wait_for_comments(page, timeout_ms: int) -> bool:
    deadline = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < deadline:
        selector, _ = _comment_nodes(page)
        if selector is not None:
            return True
        page.wait_for_timeout(500)
    return False


def _operator_handover(page) -> None:
    """Give the operator a chance to open the Comments before we save the page."""
    print(
        f"No candidate Comment selector matched within {_PANEL_WAIT_MS // 1000}s "
        f"(tried: {', '.join(COMMENT_NODE_CANDIDATES)}).",
    )
    print(
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
        f"{_OPERATOR_DEADLINE_S // 60} minutes for the Comment nodes to appear."
    )
    deadline = time.monotonic() + _OPERATOR_DEADLINE_S
    while time.monotonic() < deadline:
        page.wait_for_timeout(_OPERATOR_POLL_MS)
        if _comment_nodes(page)[0] is not None:
            print("Comment nodes found; capturing.")
            return
        print(f"  still waiting (~{int(deadline - time.monotonic())}s left)")
    print("Gave up waiting for the Comment nodes; capturing what is on the page.")


def scroll_to_load_all(page) -> int:
    """Drive the panel's scroll container until nothing new arrives.

    Returns the number of polls spent scrolling, for the sidecar. Bounded by
    `_SCROLL_DEADLINE_S` so an infinite feed cannot hang the operator.
    """
    _, locator = _comment_nodes(page)
    if locator is None:
        return 0
    started = time.monotonic()
    stable = 0
    last_count = locator.count()
    polls = 0
    while time.monotonic() - started < _SCROLL_DEADLINE_S:
        try:
            page.evaluate(_SCROLL_TO_END_JS)
        except Exception:
            pass
        page.wait_for_timeout(_SCROLL_POLL_MS)
        polls += 1
        _, locator = _comment_nodes(page)
        current = locator.count() if locator is not None else 0
        if current > last_count:
            print(f"  scroll: {last_count} -> {current} Comment nodes")
            last_count = current
            stable = 0
        else:
            stable += 1
            if stable >= _SCROLL_STABLE_POLLS:
                break
    return polls


def summarise(page, responses: list[dict]) -> dict:
    """What this capture holds, and how it knows."""
    selectors = count_selectors(page)
    selector, locator = _comment_nodes(page)
    nodes = locator.count() if locator is not None else 0

    with_text = 0
    with_author = 0
    samples: list[dict] = []
    for index in range(min(nodes, 50)):  # a sample, never the whole corpus
        text, author = _text_and_author(locator.nth(index))
        with_text += 1 if text else 0
        with_author += 1 if author else 0
        if index < 3:
            samples.append({"text_chars": len(text), "has_author": bool(author)})

    api_cids: list[str] = []
    totals: list[int] = []
    for record in responses:
        for cid in record.get("cids", []):
            if cid not in api_cids:
                api_cids.append(cid)
        if record.get("total") is not None:
            totals.append(record["total"])

    # The API's total is the only completeness signal. A late response may
    # restate it; the last one is the freshest.
    reported_total = totals[-1] if totals else None
    if not responses:
        completeness = "unknown"
    elif reported_total is None:
        completeness = "unknown"
    elif len(api_cids) >= reported_total:
        completeness = "complete"
    else:
        completeness = "truncated"

    return {
        "state_script_present": _count(page, _STATE_SCRIPT_SELECTOR) == 1,
        "comment_selector_used": selector,
        "selector_counts": selectors,
        "comment_nodes": nodes,
        "comment_nodes_with_text": with_text,
        "comment_nodes_with_author": with_author,
        "samples": samples,
        "identifier": {
            "dom_attributes_found": 0,
            "api_cids": len(api_cids),
            "api_cids_sample": api_cids[:3],
        },
        "comment_list_responses": len(responses),
        "reported_total": reported_total,
        "has_more": (responses[-1].get("has_more") if responses else None),
        "completeness": completeness,
    }


def warnings_for(summary: dict) -> list[str]:
    """Every reason this capture would be a wasted trip, in plain words."""
    warnings: list[str] = []
    if summary["comment_nodes"] == 0:
        warnings.append(
            "No Comment node matched any candidate selector, so the adapter has "
            "nothing to read. If Comments are visible on screen, every selector "
            "has rotated and the sidecar's counts are the evidence."
        )
    elif summary["comment_nodes_with_text"] == 0:
        warnings.append(
            "Comment nodes matched but none yielded text; the text selector has "
            "likely moved too."
        )
    if summary["comment_list_responses"] == 0:
        warnings.append(
            "The page made no /api/comment/list request, so there is no cid and no "
            "total. Without that response the corpus cannot state its own completeness."
        )
    elif summary["reported_total"] is not None and summary["completeness"] == "truncated":
        warnings.append(
            f"The API reported total {summary['reported_total']} but only "
            f"{summary['identifier']['api_cids']} cids were seen across "
            f"{summary['comment_list_responses']} response(s). Treat the capture as "
            "truncated, not as the whole section."
        )
    if not summary["state_script_present"]:
        warnings.append(
            "The rehydration script is absent; the adapter must not rely on it for total."
        )
    return warnings


def _existing_ancestor(path: Path) -> Path:
    """`path`, or its nearest ancestor that exists (a fresh `data/captures` does not)."""
    candidate = path
    while not candidate.exists() and candidate.parent != candidate:
        candidate = candidate.parent
    return candidate


def _repo_root_of(path: Path) -> Path | None:
    """The work tree `path` is inside, or None when it is outside git."""
    start = _existing_ancestor(path if path.is_dir() else path.parent)
    try:
        result = subprocess.run(
            ["git", "-C", str(start), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    return Path(result.stdout.strip()).resolve()


def _inside_repo(path: Path) -> bool:
    return _repo_root_of(path) is not None


def _git_ignored(path: Path) -> bool:
    root = _repo_root_of(path)
    if root is None:
        return False
    result = subprocess.run(
        ["git", "-C", str(root), "check-ignore", "-q", "--", str(path.resolve())],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Operator-run capture tool. Requires a logged-in Session and a visible browser."
    )
    parser.add_argument("account", help="Account name whose Session is already logged in")
    parser.add_argument("url", help="TikTok Post URL to capture")
    parser.add_argument(
        "path",
        nargs="?",
        help="Destination HTML path (default: data/captures/tiktok-<post>-<timestamp>.html)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Write inside the repository even where git does not ignore the path",
    )
    args = parser.parse_args(argv)

    if args.path:
        destination = Path(args.path).expanduser().resolve()
    else:
        post = re.sub(r"[^0-9a-zA-Z]+", "-", args.url.rstrip("/").rsplit("/", 1)[-1]).strip("-")
        stamp = time.strftime("%Y%m%dT%H%M%S")
        destination = (REPO_ROOT / "data" / "captures" / f"tiktok-{post or 'post'}-{stamp}.html")
    destination.parent.mkdir(parents=True, exist_ok=True)

    if _inside_repo(destination) and not _git_ignored(destination) and not args.force:
        print(
            f"refusing to write {destination}: it is inside the repository and not "
            "git-ignored, and a capture carries third parties' Comment text. Use "
            "data/captures/ (git-ignored) or pass --force if that is deliberate.",
            file=sys.stderr,
        )
        return 2

    responses: list[dict] = []
    stored: list[Any] = []

    def _on_response(response) -> None:
        if is_comment_list_response(response.url):
            stored.append(response)

    with session(args.account, headless=False) as ctx:
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.on("response", _on_response)
        page.goto(args.url, wait_until="domcontentloaded")
        if not _wait_for_comments(page, _PANEL_WAIT_MS):
            _operator_handover(page)
        page.wait_for_timeout(_SETTLE_MS)

        scroll_to_load_all(page)
        page.wait_for_timeout(_SETTLE_MS)

        # Responses are read after the page settles, not inside the handler: a
        # body is still fetchable from a stored Response, and reading it in the
        # handler runs sync IO on the dispatch that may be producing it.
        for response in stored:
            record = read_comment_list_response(response)
            if record is not None:
                responses.append(record)

        summary = summarise(page, responses)
        warnings = warnings_for(summary)
        html = page.content()

    destination.write_text(html, encoding="utf-8")
    sidecar = destination.with_suffix(destination.suffix + ".capture.json")
    sidecar.write_text(
        json.dumps(
            {
                "url": args.url,
                "account": args.account,
                "captured_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "page": str(destination),
                **summary,
                "warnings": warnings,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    # The raw responses are the cid corpus; keep them beside the page so the
    # adapter can be checked against them rather than against a memory of them.
    comment_list = destination.with_suffix(destination.suffix + ".comment-list.json")
    comment_list.write_text(json.dumps(responses, indent=2) + "\n", encoding="utf-8")

    print(f"saved Recorded page to {destination}")
    print(f"saved capture summary to {sidecar}")
    print(f"saved comment/list responses to {comment_list}")
    print(json.dumps(summary, indent=2))
    for warning in warnings:
        print(f"WARNING: {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
