from datetime import datetime, timezone
from pathlib import Path

import pytest

from agent.adapters.tiktok import (
    SelectorRot,
    TikTokRecordedPageAdapter,
    TruncatedRead,
    UnreadableTotal,
)

FIXTURES = Path(__file__).parent / "fixtures" / "recorded"


def fixture_path(name: str) -> Path:
    return FIXTURES / name


def test_reads_without_a_session():
    result = TikTokRecordedPageAdapter().read_comments(fixture_path("tiktok_complete.html"))

    assert result.total == 3
    assert [comment.text for comment in result.comments] == [
        "invented comment alpha",
        "invented comment beta",
        "invented comment gamma",
    ]


def test_every_comment_carries_its_identifier():
    result = TikTokRecordedPageAdapter().read_comments(fixture_path("tiktok_complete.html"))

    assert [comment.identity for comment in result.comments] == ["c-100", "c-101", "c-102"]
    assert all(comment.identity for comment in result.comments)


def test_every_comment_carries_its_creation_time_when_the_shape_has_one():
    result = TikTokRecordedPageAdapter().read_comments(fixture_path("tiktok_pass.html"))

    comment = next(comment for comment in result.comments if comment.identity == "c-old")
    assert comment.created_at == datetime(
        2026, 10, 20, 10, 0, tzinfo=timezone.utc
    )
    assert comment.created_at.tzinfo is timezone.utc


def test_a_missing_creation_time_is_none_not_a_guessed_time():
    result = TikTokRecordedPageAdapter().read_comments(fixture_path("tiktok_pass.html"))

    comment = next(comment for comment in result.comments if comment.identity == "c-missing")
    assert comment.created_at is None


@pytest.mark.parametrize(
    "fixture_name, expected_total, expected_read",
    [
        ("tiktok_total_four_but_three_comments.html", 4, 3),
        ("tiktok_total_two_but_three_comments.html", 2, 3),
    ],
)
def test_completeness_is_asserted_not_assumed(fixture_name: str, expected_total: int, expected_read: int):
    with pytest.raises(TruncatedRead, match=rf"total {expected_total}, read {expected_read}"):
        TikTokRecordedPageAdapter().read_comments(fixture_path(fixture_name))


def test_has_more_zero_is_not_evidence_of_completion():
    with pytest.raises(TruncatedRead, match=r"total 5, read 2"):
        TikTokRecordedPageAdapter().read_comments(
            fixture_path("tiktok_has_more_zero_but_total_larger.html")
        )


def test_selector_rot_fails_loudly():
    with pytest.raises(SelectorRot, match=r"missing its identifier"):
        TikTokRecordedPageAdapter().read_comments(fixture_path("tiktok_selector_rot.html"))


def test_total_absent_or_unreadable_is_not_treated_as_zero():
    with pytest.raises(UnreadableTotal, match=r"total"):
        TikTokRecordedPageAdapter().read_comments(fixture_path("tiktok_total_absent.html"))
