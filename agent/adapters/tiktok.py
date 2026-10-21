"""Read TikTok Comments from a Recorded page."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from playwright.sync_api import Error, sync_playwright

from agent.recorded_page import recorded_page

_COMMENT_PANEL_SELECTOR = '[data-e2e="comment-level-1"]'
_COMMENT_LIST_ITEM_SELECTOR = '[data-e2e="comment-level-1"] > *'
_COMMENT_ID_ATTR = 'data-comment-id'
_COMMENT_TEXT_SELECTOR = '[data-e2e="comment-text"]'
_TOTAL_SELECTOR = '[data-e2e="comment-count"]'
_STATE_SCRIPT_SELECTOR = 'script[id="__UNIVERSAL_DATA_FOR_REHYDRATION__"]'


class TruncatedRead(RuntimeError):
    """The Platform reported more or fewer Comments than were read."""


class SelectorRot(RuntimeError):
    """A locator matched, but no longer to the expected element."""


class UnreadableTotal(RuntimeError):
    """The page's reported total could not be read."""


@dataclass(frozen=True)
class Comment:
    identity: str
    text: str


@dataclass(frozen=True)
class PostComments:
    comments: tuple[Comment, ...]
    total: int


class TikTokRecordedPageAdapter:
    """Reads one TikTok Post's Comments from a Recorded page."""

    def read_comments(self, path: str | Path) -> PostComments:
        with recorded_page(path) as url:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True)
                page = browser.new_page()
                try:
                    page.goto(url, wait_until="domcontentloaded")
                    page.wait_for_selector(_COMMENT_PANEL_SELECTOR)
                    total = _read_total(page)
                    comments = _read_comments(page)
                    if len(comments) != total:
                        raise TruncatedRead(
                            f"TikTok Recorded page reported total {total}, read {len(comments)}"
                        )
                    return PostComments(comments=tuple(comments), total=total)
                finally:
                    browser.close()


def _read_total(page) -> int:
    state = _read_state_total(page)
    if state is not None:
        return state

    locator = page.locator(_TOTAL_SELECTOR)
    if locator.count() != 1:
        raise UnreadableTotal("TikTok Recorded page total is absent or ambiguous")
    text = (locator.first.text_content() or "").strip()
    digits = "".join(ch for ch in text if ch.isdigit())
    if not digits:
        raise UnreadableTotal(f"TikTok Recorded page total is unreadable: {text!r}")
    return int(digits)


def _read_state_total(page) -> int | None:
    locator = page.locator(_STATE_SCRIPT_SELECTOR)
    if locator.count() == 0:
        return None
    if locator.count() != 1:
        raise SelectorRot("TikTok Recorded page state script is ambiguous")
    raw = locator.first.text_content() or ""
    if not raw.strip():
        raise UnreadableTotal("TikTok Recorded page state script is empty")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise UnreadableTotal("TikTok Recorded page state script is not valid JSON") from exc
    total = _find_total(payload)
    if total is None:
        raise UnreadableTotal("TikTok Recorded page total is absent from state")
    return total


def _find_total(value: Any) -> int | None:
    if isinstance(value, dict):
        for key in ("total", "commentsTotal", "commentCount"):
            candidate = value.get(key)
            if isinstance(candidate, int):
                return candidate
            if isinstance(candidate, str) and candidate.isdigit():
                return int(candidate)
        for nested in value.values():
            found = _find_total(nested)
            if found is not None:
                return found
    elif isinstance(value, list):
        for nested in value:
            found = _find_total(nested)
            if found is not None:
                return found
    return None


def _read_comments(page) -> list[Comment]:
    panel = page.locator(_COMMENT_PANEL_SELECTOR)
    if panel.count() != 1:
        raise SelectorRot("TikTok Comment panel locator no longer identifies exactly one panel")

    items = page.locator(_COMMENT_LIST_ITEM_SELECTOR)
    comments: list[Comment] = []
    for index in range(items.count()):
        item = items.nth(index)
        identity = (item.get_attribute(_COMMENT_ID_ATTR) or "").strip()
        if not identity:
            raise SelectorRot(f"TikTok Comment {index} is missing its identifier")

        text_locator = item.locator(_COMMENT_TEXT_SELECTOR)
        if text_locator.count() != 1:
            raise SelectorRot(
                f"TikTok Comment {index} text locator matched {text_locator.count()} elements"
            )
        text = (text_locator.first.text_content() or "").strip()
        comments.append(Comment(identity=identity, text=text))
    return comments
