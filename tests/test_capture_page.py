"""The capture tool's two jobs: find the Comments that are on the page, and say
what it did *not* find.

Every fixture page here is invented (D16). The live-page selectors are not
invented: `docs/research/comment-identity.md` names them, and the smoke page is
shaped to match so that a tool which silently reverts to the old `comment-level`
container selector fails this suite rather than an operator's afternoon.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from agent.recorded_page import recorded_page
from tools import capture_page

_SMOKE = Path(__file__).parent / "fixtures" / "capture_smoke" / "page.html"


# --- the response parser, without a browser ----------------------------------


def test_the_response_parser_reads_the_fields_completeness_depends_on():
    record = capture_page.parse_comment_list(
        {
            "comments": [{"cid": "1"}, {"cid": 2}, {"text": "no cid"}],
            "cursor": 40,
            "has_more": 1,
            "total": 569,
        }
    )

    assert record["cids"] == ["1", "2"]
    assert record["comments"] == 3
    assert (record["total"], record["has_more"], record["cursor"]) == (569, 1, 40)


def test_the_response_parser_accepts_a_nested_data_object_and_string_numbers():
    record = capture_page.parse_comment_list(
        {"data": {"comments": [{"cid": "7"}], "total": "9", "has_more": "0"}}
    )

    assert record["cids"] == ["7"]
    assert record["total"] == 9
    assert record["has_more"] == 0


@pytest.mark.parametrize("payload", [None, [], "nope", {"unrelated": 1}, {"data": []}])
def test_the_response_parser_never_invents_fields(payload):
    record = capture_page.parse_comment_list(payload)

    assert record["cids"] == []
    assert record["total"] is None
    assert record["has_more"] is None


def test_only_the_top_level_comment_list_endpoint_counts_as_one():
    assert capture_page.is_comment_list_response(
        "https://www.tiktok.com/api/comment/list/?aweme_id=1&cursor=0"
    )
    # The reply endpoint's `total` counts replies, not the section, so it must
    # not reach the completeness check.
    assert not capture_page.is_comment_list_response(
        "https://www.tiktok.com/api/comment/list/reply/?comment_id=1"
    )
    assert not capture_page.is_comment_list_response(
        "https://www.tiktok.com/api/comment/list/is/elsewhere"
    )
    assert not capture_page.is_comment_list_response(
        "https://www.tiktok.com/api/related/item_list/?aweme_id=1"
    )


# --- the smoke page, in a real browser ---------------------------------------


@pytest.fixture
def smoke_page():
    with recorded_page(_SMOKE) as url:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page()
            stored: list = []
            page.on(
                "response",
                lambda r: stored.append(r)
                if capture_page.is_comment_list_response(r.url)
                else None,
            )
            page.goto(url, wait_until="domcontentloaded")
            page.wait_for_timeout(500)
            try:
                yield page, stored
            finally:
                browser.close()


def test_the_smoke_page_is_read_by_the_research_selector_not_the_old_one(smoke_page):
    page, _ = smoke_page

    counts = capture_page.count_selectors(page)
    summary = capture_page.summarise(page, [])

    assert summary["comment_selector_used"] == '[class*="DivCommentItem"]'
    assert summary["comment_nodes"] == 2
    assert summary["comment_nodes_with_text"] == 2
    assert summary["comment_nodes_with_author"] == 2
    # `comment-level-1` is present -- twice -- but as the text span inside each
    # Comment, which is the trap the research doc records. It must never be
    # mistaken for the Comment set, or the corpus doubles and every row is text.
    assert counts['[data-e2e^="comment-level"]'] == 2
    assert summary["comment_nodes"] == 2


def test_the_capture_records_cids_and_total_from_the_pages_own_request(smoke_page):
    page, stored = smoke_page

    records = [
        record
        for record in (capture_page.read_comment_list_response(r) for r in stored)
        if record is not None
    ]
    summary = capture_page.summarise(page, records)

    assert [record["total"] for record in records] == [2]
    assert summary["identifier"]["api_cids"] == 2
    assert summary["reported_total"] == 2
    assert summary["completeness"] == "complete"
    assert capture_page.warnings_for(summary) == []


def test_a_page_with_no_api_response_is_reported_as_unknown_not_complete(smoke_page):
    page, _ = smoke_page

    summary = capture_page.summarise(page, [])
    warnings = capture_page.warnings_for(summary)

    assert summary["completeness"] == "unknown"
    assert any("no /api/comment/list request" in warning for warning in warnings)


def test_a_partial_read_is_called_truncated(smoke_page):
    page, _ = smoke_page

    summary = capture_page.summarise(
        page,
        [{"cids": ["1"], "total": 569, "has_more": 0}],
    )
    warnings = capture_page.warnings_for(summary)

    assert summary["completeness"] == "truncated"
    assert any("truncated" in warning for warning in warnings)


def test_the_default_destination_is_inside_the_git_ignored_data_directory():
    # Not a run: just the rule the operator is promised. `main` computes this
    # the same way when no path is given.
    default = capture_page.REPO_ROOT / "data" / "captures"
    assert capture_page._git_ignored(default / "example.html")
