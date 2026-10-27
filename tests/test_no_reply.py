"""The structural No-reply test (ADR 0018, D2).

The test is "does this Comment present anything addressed to the organisation?",
never "did any entry match". These tests pin the three shapes decidable from text
today and, just as importantly, the direction of every ambiguity: toward ``None``
(reach the Router), never toward swallowing a plea.
"""

from __future__ import annotations

import pytest

from agent.no_reply import NoReplyReason, no_reply_reason


@pytest.mark.parametrize("text", ["alhamdulillah", "Alhamdulillah", "masya allah"])
def test_a_bare_formula_is_a_no_reply_reason(text: str) -> None:
    assert no_reply_reason(text) is NoReplyReason.BARE_FORMULA


def test_a_formula_with_content_after_it_is_not_a_bare_formula() -> None:
    # The reason bare_interjection exists: "every word is a formula word", not
    # "contains a formula word". This Comment is a DOA_BLESSING and must reach
    # the Router, not be silenced (ADR 0018).
    assert no_reply_reason("alhamdulillah semoga cepat sembuh") is None


@pytest.mark.parametrize("text", ["\U0001f970\U0001f970\U0001f970", "\U0001f62d\U0001f62d\U0001f62d"])
def test_an_emoji_only_comment_is_a_no_reply_reason(text: str) -> None:
    assert no_reply_reason(text) is NoReplyReason.EMPTY


@pytest.mark.parametrize("text", ["@organisasi", "@org @kawan"])
def test_a_mention_only_comment_is_a_no_reply_reason(text: str) -> None:
    assert no_reply_reason(text) is NoReplyReason.MENTION_OR_SUPPORT_TAG


@pytest.mark.parametrize("text", ["#support", "#hadir #support"])
def test_a_support_tag_only_comment_is_a_no_reply_reason(text: str) -> None:
    assert no_reply_reason(text) is NoReplyReason.MENTION_OR_SUPPORT_TAG


@pytest.mark.parametrize(
    "text",
    [
        "@org berapa harga",  # a mention *and* a question
        "#support tolong bantu saya",  # a tag *and* a plea
        "salam @org",
    ],
)
def test_a_mention_or_tag_carrying_content_reaches_the_router(text: str) -> None:
    # Widening the mention/tag shape to swallow a plea is the failure ADR 0018
    # names, so anything that also carries a word-bearing token returns None.
    assert no_reply_reason(text) is None


def test_chatter_between_commenters_is_not_guessed_from_text() -> None:
    # "Chatter between commenters" is a structural fact about the page -- one
    # person replying to another -- and `agent.adapters.tiktok.Comment` carries
    # no such field. It is named in the module docstring as awaiting the Adapter's
    # structure (ticket #16) rather than detected from words. This test pins that
    # no word-level heuristic has been invented for it.
    assert no_reply_reason("hahaha betul tu bang") is None


def test_an_ordinary_comment_reaches_the_router() -> None:
    assert no_reply_reason("berapa harga") is None
    assert no_reply_reason("terima kasih") is None


def test_the_reason_is_a_named_value_not_a_bool() -> None:
    # A bare bool would throw away *why* the Comment is silent, which the record
    # and the sink need to stay auditable.
    reasons = {reason.value for reason in NoReplyReason}
    assert len(reasons) == 3
