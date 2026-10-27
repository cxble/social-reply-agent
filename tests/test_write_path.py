"""The write path, exercised against a Recorded page with no Session.

Each test maps to one acceptance criterion of ticket 7. The write path is not
wired into the Comment pass (D1): it is exercised directly, on its own
:class:`WritePage` seam. "Recorded page" here is the double below, which models a
saved page honestly -- it re-finds a Comment by its body text (the only way the
page can be re-found), it can report a different identifier than the one held, and
it can fail to read back the Reply it was asked to post. No network, no Session.
The live submit against real selectors is #16's (D5).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import pytest

from agent.comment_pass import EscalationSink
from agent.adapters.tiktok import TikTokRecordedPageAdapter
from agent.record import CommentRecord, CommentStore, Outcome, ReplyStatus
from agent.write_path import (
    CommentWriter,
    Confirmation,
    HeldComment,
    IdentifierUnreadable,
)

NOW = datetime(2026, 10, 28, 12, 0, tzinfo=timezone.utc)
FIXTURES = Path(__file__).parent / "fixtures" / "recorded"


@dataclass
class RenderedComment:
    """One Comment as the page currently shows it.

    ``identity`` is ``None`` when the identifier cannot be read off the page -- the
    failure Bar 4 must not paper over with text.
    """

    identity: str | None
    text: str
    replies: list[tuple[str, str]] = field(default_factory=list)


class RecordedPage:
    """A saved page that models a real one honestly, without a Session.

    It re-finds a Comment the way a real page must -- by body text, because the
    identifier does not locate the element (see ``docs/research/comment-identity.md``)
    -- and reports the identifier it now carries. That gap between "found by text"
    and "the identifier decides" is exactly what Bar 4 pins.
    """

    def __init__(
        self,
        comments: list[RenderedComment],
        *,
        account: str = "acct",
        echo: bool = True,
        moved_after_submit: bool = False,
        raises_on_submit: bool = False,
    ) -> None:
        self._comments = list(comments)
        self.account = account
        self.echo = echo
        self.moved_after_submit = moved_after_submit
        self.raises_on_submit = raises_on_submit
        self.submitted: list[tuple[str | None, str]] = []
        self.calls: list[str] = []

    def _re_find(self, comment: HeldComment) -> RenderedComment:
        matches = [c for c in self._comments if c.text == comment.text]
        if len(matches) != 1:
            raise IdentifierUnreadable(
                f"could not re-find the Comment by its text ({len(matches)} matches)"
            )
        return matches[0]

    def re_read_identifier(self, comment: HeldComment) -> str:
        self.calls.append("re_read_identifier")
        rendered = self._re_find(comment)
        if rendered.identity is None:
            raise IdentifierUnreadable(
                "the Comment's identifier is absent from the page"
            )
        return rendered.identity

    def submit_reply(self, comment: HeldComment, reply_text: str) -> None:
        self.calls.append("submit_reply")
        if self.raises_on_submit:
            # A page can fail while submitting and still have posted: the outcome
            # is genuinely unknown, which is the case this models.
            raise RuntimeError("the page failed while submitting")
        rendered = self._re_find(comment)
        self.submitted.append((rendered.identity, reply_text))
        if self.moved_after_submit and rendered.identity is not None:
            rendered.identity = f"{rendered.identity}-moved"
        if self.echo:
            rendered.replies.append((self.account, reply_text))

    def read_confirmation(self, comment: HeldComment) -> Confirmation | None:
        self.calls.append("read_confirmation")
        for rendered in self._comments:
            if rendered.identity != comment.identity:
                continue
            for author, _text in rendered.replies:
                return Confirmation(identity=rendered.identity, account=author)
        return None


@pytest.fixture
def store(tmp_path):
    s = CommentStore(tmp_path / "acct.sqlite3", account="acct")
    yield s
    s.close()


def _writer(store, tmp_path, page) -> CommentWriter:
    return CommentWriter(
        account="acct",
        page=page,
        store=store,
        escalations=EscalationSink(tmp_path / "acct.escalations.jsonl"),
        now=lambda: NOW,
    )


def _held(
    *, identity: str = "c-1", text: str = "please help", post: str = "p-1"
) -> HeldComment:
    return HeldComment(platform="tiktok", post=post, identity=identity, text=text)


def _escalations(tmp_path) -> list[dict]:
    path = tmp_path / "acct.escalations.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines()]


# --- AC 1, AC 4, AC 5: re-find, submit, and read the Confirmation back --------


def test_the_held_comment_is_read_off_a_real_recorded_page_with_no_session(
    store, tmp_path
):
    # AC 5 in its literal form: the Comment the write path holds comes off a real
    # Recorded page, served on localhost and read by the Adapter -- no Session, no
    # network. The submit/read-back seam is the double, because the live submit
    # against real selectors is #16's (D5).
    read = TikTokRecordedPageAdapter().read_comments(FIXTURES / "tiktok_pass.html")
    page = RecordedPage(
        [RenderedComment(identity=c.identity, text=c.text) for c in read.comments]
    )
    writer = _writer(store, tmp_path, page)
    mid = next(c for c in read.comments if c.identity == "c-mid")

    result = writer.write_reply(
        HeldComment(
            platform="tiktok", post="p-1", identity=mid.identity, text=mid.text
        ),
        "Salam, terima kasih!",
    )

    assert result.wrote is True
    assert page.submitted == [("c-mid", "Salam, terima kasih!")]


def test_it_re_finds_submits_and_reads_back_the_confirmation(store, tmp_path):
    page = RecordedPage([RenderedComment(identity="c-1", text="please help")])
    writer = _writer(store, tmp_path, page)

    result = writer.write_reply(_held(), "Salam, terima kasih!")

    assert result.wrote is True
    assert result.escalated is False
    assert result.outcome is Outcome.CANNED_REPLY
    assert page.submitted == [("c-1", "Salam, terima kasih!")]
    # The page was read back *after* the submit, not before it.
    assert page.calls == ["re_read_identifier", "submit_reply", "read_confirmation"]

    record = store.get("tiktok", "c-1")
    assert record.outcome is Outcome.CANNED_REPLY
    assert record.reply_status is ReplyStatus.ANSWERED_BY_ACCOUNT
    assert store.contains("tiktok", "c-1")
    assert _escalations(tmp_path) == []


# --- AC 2: a mismatch, or an unreadable identifier, skips and Escalates -------


def test_an_identical_text_under_a_different_identifier_is_never_written(
    store, tmp_path
):
    # The page re-finds a Comment whose text is byte-identical to the one held but
    # whose identifier differs. A text fallback would write here; the identifier
    # guard must not. This is the pin that catches a well-meaning content fallback.
    page = RecordedPage([RenderedComment(identity="c-OTHER", text="please help")])
    writer = _writer(store, tmp_path, page)

    result = writer.write_reply(_held(identity="c-1", text="please help"), "hi")

    assert result.wrote is False
    assert result.escalated is True
    assert result.outcome is Outcome.UNCONFIRMED_IDENTIFIER
    assert page.submitted == []
    assert store.get("tiktok", "c-1").outcome is Outcome.UNCONFIRMED_IDENTIFIER
    (entry,) = _escalations(tmp_path)
    assert entry["identity"] == "c-1"
    assert entry["outcome"] == "UNCONFIRMED_IDENTIFIER"


def test_an_unreadable_identifier_is_not_written_and_the_failure_names_why(
    store, tmp_path
):
    page = RecordedPage([RenderedComment(identity=None, text="please help")])
    writer = _writer(store, tmp_path, page)

    result = writer.write_reply(_held(), "hi")

    assert result.wrote is False
    assert result.escalated is True
    assert result.outcome is Outcome.UNCONFIRMED_IDENTIFIER
    assert page.submitted == []
    assert "identifier" in result.detail
    assert "absent from the page" in result.detail
    (entry,) = _escalations(tmp_path)
    assert entry["outcome"] == "UNCONFIRMED_IDENTIFIER"
    assert "absent from the page" in entry["detail"]


# --- AC 3: a Comment edited after it was read gets no second Reply ------------


def test_a_comment_edited_after_it_was_read_is_not_written_a_second_time(
    store, tmp_path
):
    # The load-bearing test. A Reply is already recorded for this identifier. The
    # Comment's text is then edited, and the write path is handed it again with the
    # *new* text. Because the Replied set keys on the identifier and not on a hash
    # of the text (ADR 0007), it is still there and no second write happens. This is
    # the test that would fail if the key were ever switched to the text.
    store.record(
        CommentRecord(
            platform="tiktok",
            identity="c-1",
            text="original words",
            baseline=False,
            outcome=Outcome.CANNED_REPLY,
            reply_status=ReplyStatus.ANSWERED_BY_ACCOUNT,
        )
    )
    page = RecordedPage([RenderedComment(identity="c-1", text="edited words")])
    writer = _writer(store, tmp_path, page)

    result = writer.write_reply(_held(text="edited words"), "hi again")

    assert result.wrote is False
    assert result.submitted is False
    assert result.escalated is False
    assert page.submitted == []
    # The page was not even re-read: the Replied set short-circuits the write.
    assert page.calls == []
    assert store.get("tiktok", "c-1").text == "original words"
    assert _escalations(tmp_path) == []


# --- AC 4: a write that cannot be confirmed is not a success ------------------


def test_a_submitted_write_that_cannot_be_confirmed_is_not_a_success(
    store, tmp_path
):
    # The page accepts the submit but nothing reads back. This is neither posted
    # nor not-posted: an Unknown outcome, Escalated loudly and left to
    # Reconciliation. silence would hide a possible public duplicate Reply.
    page = RecordedPage(
        [RenderedComment(identity="c-1", text="please help")], echo=False
    )
    writer = _writer(store, tmp_path, page)

    result = writer.write_reply(_held(), "hi")

    assert result.submitted is True
    assert result.wrote is False
    assert result.escalated is True
    assert result.outcome is Outcome.UNKNOWN_OUTCOME
    assert page.submitted == [("c-1", "hi")]
    assert store.get("tiktok", "c-1").outcome is Outcome.UNKNOWN_OUTCOME
    (entry,) = _escalations(tmp_path)
    assert entry["outcome"] == "UNKNOWN_OUTCOME"
    assert "not confirmed" in entry["detail"]


def test_a_submit_that_raises_is_an_unknown_outcome_not_a_lost_write(store, tmp_path):
    # The page throws while submitting: the click may or may not have landed, so
    # the result is unknown. Letting that exception out of write_reply would leave
    # no record and no Escalation -- and because nothing was recorded, the Replied
    # set would still be empty and a later run would try the Comment again. That
    # second attempt is the public duplicate Reply ADR 0019 calls "the largest
    # correctness risk in this project", reached without anyone editing anything.
    page = RecordedPage(
        [RenderedComment(identity="c-1", text="please help")], raises_on_submit=True
    )
    writer = _writer(store, tmp_path, page)

    result = writer.write_reply(_held(), "hi")

    assert result.wrote is False
    assert result.submitted is True
    assert result.escalated is True
    assert result.outcome is Outcome.UNKNOWN_OUTCOME
    assert store.get("tiktok", "c-1").outcome is Outcome.UNKNOWN_OUTCOME
    (entry,) = _escalations(tmp_path)
    assert entry["outcome"] == "UNKNOWN_OUTCOME"
    # The detail has to carry the failure, or a swallowed bug is invisible.
    assert "failed while submitting" in entry["detail"]

    # And the record is what stops the retry: a second run finds the Comment
    # already handled and does not submit again.
    again = writer.write_reply(_held(), "hi")
    assert again.outcome is None
    assert page.calls.count("submit_reply") == 1


def test_an_unreadable_identifier_is_not_wrapped_in_an_unknown_outcome(store, tmp_path):
    # The other side of the same guard. Before any submit, a failure that is not
    # the page's declared way of saying "I cannot read this" is a bug, not a
    # write of unknown result -- nothing can have posted, so it propagates rather
    # than being recorded as an Unknown outcome a human would have to chase.
    class BrokenPage(RecordedPage):
        def re_read_identifier(self, comment):
            raise ValueError("a bug in the page, not an unreadable identifier")

    page = BrokenPage([RenderedComment(identity="c-1", text="please help")])
    writer = _writer(store, tmp_path, page)

    with pytest.raises(ValueError):
        writer.write_reply(_held(), "hi")

    assert page.calls == []
    assert _escalations(tmp_path) == []


def test_a_confirmation_attributed_to_another_account_is_not_a_success(
    store, tmp_path
):
    # The Reply reads back, but not as this Account -- so it is not this write's
    # Confirmation. The write is still unconfirmed.
    page = RecordedPage(
        [
            RenderedComment(
                identity="c-1",
                text="please help",
                replies=[("someone-else", "not ours")],
            )
        ],
        echo=False,
    )
    writer = _writer(store, tmp_path, page)

    result = writer.write_reply(_held(), "hi")

    assert result.wrote is False
    assert result.outcome is Outcome.UNKNOWN_OUTCOME
    assert "someone-else" in result.detail


def test_a_confirmation_that_moved_off_the_comment_is_not_a_success(store, tmp_path):
    # The page reads back, but the identifier it reports is no longer the one the
    # write was meant for. The Confirmation is against the wrong Comment.
    page = RecordedPage(
        [RenderedComment(identity="c-1", text="please help")],
        moved_after_submit=True,
    )
    writer = _writer(store, tmp_path, page)

    result = writer.write_reply(_held(), "hi")

    assert result.submitted is True
    assert result.wrote is False
    assert result.outcome is Outcome.UNKNOWN_OUTCOME


# --- The seam with the pass: a decision is not a Reply ------------------------
#
# The pass records a row for every Comment it decides, `CANNED_REPLY` included
# (agent/comment_pass.py), because the record is the Verdict and outcomes are
# insert-only. In the pipeline that makes the writer's Comment *already recorded*
# before it is ever asked to post -- so "there is a row" and "there is a Reply"
# have to stay two different questions (ADR 0008). These three tests are the ones
# that fail if anyone collapses them back into one.


def _decided(store, *, identity: str = "c-1", text: str = "please help") -> None:
    """Record one Comment exactly as the pass records it: verdict, no Reply yet."""
    store.record(
        CommentRecord(
            platform="tiktok",
            identity=identity,
            text=text,
            baseline=False,
            outcome=Outcome.CANNED_REPLY,
        )
    )


def test_a_comment_the_pass_already_decided_is_still_written(store, tmp_path):
    # The pass decided CANNED_REPLY and recorded it with reply_status UNKNOWN,
    # which is what "no Reply visible" means (ADR 0008). Carrying that decision
    # out is not a second decision, so the writer must post it -- and repair the
    # Reply status, because the Verdict itself is insert-only and never rewritten.
    _decided(store)
    page = RecordedPage([RenderedComment(identity="c-1", text="please help")])
    writer = _writer(store, tmp_path, page)

    result = writer.write_reply(_held(), "Salam, terima kasih!")

    assert result.wrote is True
    assert page.submitted == [("c-1", "Salam, terima kasih!")]
    record = store.get("tiktok", "c-1")
    assert record.reply_status is ReplyStatus.ANSWERED_BY_ACCOUNT
    # The Verdict and the text it was decided on are untouched: repaired, not
    # rewritten.
    assert record.outcome is Outcome.CANNED_REPLY
    assert record.text == "please help"


def test_a_reply_already_recorded_is_never_posted_over(store, tmp_path):
    # The Replied set, in its own field: a Comment the page shows as answered is
    # not posted to again, whoever answered it. The two Reply statuses stay
    # distinguishable for the human -- what is undecidable here is whether a
    # third party's answer should have stopped us, and that is not this module's
    # call to make (see #23).
    _decided(store)
    store.update_reply_status("tiktok", "c-1", ReplyStatus.ANSWERED_BY_SOMEONE_ELSE)
    page = RecordedPage([RenderedComment(identity="c-1", text="please help")])
    writer = _writer(store, tmp_path, page)

    result = writer.write_reply(_held(), "hi")

    assert result.wrote is False
    assert result.submitted is False
    assert result.escalated is False
    assert page.calls == []
    assert store.get("tiktok", "c-1").reply_status is ReplyStatus.ANSWERED_BY_SOMEONE_ELSE


def test_an_escalation_for_a_decided_comment_still_reaches_the_sink(store, tmp_path):
    # The write fails after the pass has already recorded its Verdict. The sink
    # append is the part a human needs, so it must not depend on being able to
    # write the row again -- the row is not this module's to rewrite.
    _decided(store)
    page = RecordedPage([RenderedComment(identity=None, text="please help")])
    writer = _writer(store, tmp_path, page)

    result = writer.write_reply(_held(), "hi")

    assert result.wrote is False
    assert result.escalated is True
    assert result.outcome is Outcome.UNCONFIRMED_IDENTIFIER
    (entry,) = _escalations(tmp_path)
    assert entry["outcome"] == "UNCONFIRMED_IDENTIFIER"
    assert "absent from the page" in entry["detail"]
    # The Verdict stands: the record says what was decided, the sink says why the
    # write was refused. Outcomes are insert-only, so there is no honest way to
    # turn the row into UNCONFIRMED_IDENTIFIER.
    assert store.get("tiktok", "c-1").outcome is Outcome.CANNED_REPLY
