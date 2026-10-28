"""The write path: re-find the Comment, confirm its identifier, submit, read back.

**This module has no caller, and that is the design rather than an oversight.**
Proving the write mechanism and arming it are two different acts. The Comment
pass is structurally Dry run (``CommentPass`` cannot even be handed a writer --
see ``tests/test_comment_pass.py::test_dry_run_cannot_be_given_a_writer_and_refuses_if_reached``)
because ADR 0019's bars are measured there, in Verdicts, before posting is earned.
So the mechanism that *can* post lives here, on its own seam, exercised directly
by tests, until Graduation and #11's Daily cap, Pacing and Kill switch make posting
something the agent *may* do. Wiring this into the pass is a later, deliberate act;
the missing call site keeps the mechanism and the permission apart.

**Bar 4 (ADR 0019) is about *which* Comment, and text is never the answer.** The
write path holds a Platform identifier. Immediately before submitting it re-reads
the identifier the page now shows and requires it to equal the one it holds; on a
mismatch, or an identifier it cannot read at all, it writes nothing and Escalates
the Comment with :data:`agent.record.Outcome.UNCONFIRMED_IDENTIFIER`. A
content-hash or text-equality fallback would turn an edited Comment into a new one
and post a second Reply -- ADR 0019 calls that "the largest correctness risk in
this project" -- so nothing here compares the held text with the re-read text in
order to decide. The held text is used only to *locate* the Comment, the way a
person re-finds it on the page (TikTok's ``cid`` is durable but not addressable).

**Nothing here may pretend the invented selectors are verified.** The TikTok
Adapter's selectors are unverified and real TikTok Comments render only in a headed
browser (see ``agent/adapters/tiktok.py`` and #16, ADR 0013), so this module does
not touch a live page or a Session. It is built on a :class:`WritePage` seam -- the
read-back and the submit -- and the tests exercise it against a Recorded page,
which is a double that models a page honestly (it can change an identifier between
the read and the write). The Confirmation and the re-find are protocol behaviour
and are provable without a Session; the live submit against real selectors is #16's.

**A decision is not a Reply, and the row is not the Replied set.** The pass records
a Verdict for every Comment it decides, `CANNED_REPLY` included, because the record
is what the agent decided and outcomes are insert-only. So in the pipeline the
Comment the writer is asked to post is normally *already recorded* — "is there a
row?" would answer "already handled" for every Comment worth answering, and the
agent would post nothing. The writer therefore asks two questions that ADR 0008
keeps apart: whether a Reply is already recorded under this Comment
(``reply_status``), and whether the Comment was resolved without one (any Verdict
other than the ``CANNED_REPLY`` this write realises). Carrying out the pass's
``CANNED_REPLY`` Verdict is not a second decision, so the durable row is *repaired*
— ``update_reply_status`` — rather than rewritten, and an Escalation for a Comment
the pass already recorded still reaches the sink even though the row keeps its
Verdict. That last one leaves a deliberate asymmetry: a row whose Verdict is
non-escalating can have a sink entry beside it, because the record says what was
decided and the sink says why the write was refused.

**The Confirmation is read back, and an unconfirmed write is not a success.** After
submit the page is read back and must show a Reply by the Account under the Comment
the write was meant for (ADR 0007's Confirmation). A write that cannot be confirmed
is recorded as :data:`agent.record.Outcome.UNKNOWN_OUTCOME` -- the glossary's
"Unknown outcome", whose result is neither posted nor not-posted -- and Escalated
loudly. It is settled later by Reconciliation, never by retrying.

**What is written is a :class:`agent.rotation.Phrasing`, not a bare string.** ADR
0002's "the Router structurally cannot invent a Reply" rested on whoever called
``write_reply``, because the parameter was a bare ``str`` anyone could compose.
The parameter is now the value the Phrasing deck hands out -- set, entry and text
came from somewhere a Reviewer can name -- so the shape is right and the call site
auditable. It does not make invention impossible: a caller can still build a
``Phrasing`` by hand. The type narrows the honest path, and no impossibility is
claimed. The deck itself is not wired in here (that is Graduation, #14).

See `docs/reply-routing.md` step 6, ADR 0007 and ADR 0019.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

from agent.record import (
    CommentNotFound,
    CommentRecord,
    CommentStore,
    Outcome,
    ReplyStatus,
)
from agent.rotation import Phrasing

__all__ = (
    "CommentWriter",
    "Confirmation",
    "Escalations",
    "HeldComment",
    "IdentifierUnreadable",
    "WritePage",
    "WriteResult",
)


class IdentifierUnreadable(RuntimeError):
    """The page could not yield the Comment's identifier at write time.

    Raised by a :class:`WritePage` when the identifier cannot be read -- absent,
    ambiguous, or rotated away. It is the failure that must skip and Escalate the
    Comment rather than fall back to its text (ADR 0019, Bar 4).
    """


@dataclass(frozen=True)
class HeldComment:
    """The Comment the write path holds: its identifier, and where it lives.

    ``text`` is carried so the page can *locate* the Comment and so an Escalation
    can show a human what was skipped; it is never what decides the write.
    """

    platform: str
    post: str
    identity: str
    text: str


@dataclass(frozen=True)
class Confirmation:
    """A Reply read back from the page, attributable to the Account.

    The check that matters is ``identity`` equal to the one held, under the
    Account that posted (ADR 0007). This is the same mechanism as Bar 4's re-find.
    """

    identity: str
    account: str


class WritePage(Protocol):
    """The seam the write path needs: read a Comment back, and submit a Reply.

    Deliberately not the TikTok Adapter's invented selectors (#16). A Recorded
    page double implements this honestly; the live implementation is a separate,
    later act.
    """

    def re_read_identifier(self, comment: HeldComment) -> str:
        """Re-find the Comment and return the identifier it now carries.

        Raise :class:`IdentifierUnreadable` if the identifier cannot be read.
        """
        ...

    def submit_reply(self, comment: HeldComment, reply_text: str) -> None:
        """Submit ``reply_text`` against the re-found Comment."""
        ...

    def read_confirmation(self, comment: HeldComment) -> Confirmation | None:
        """The Reply read back under the Comment, or ``None`` if none reads back.

        The Reply is reported as it is on the page, whoever posted it; deciding
        whether it is the Account's is the writer's job, not the page's.
        """
        ...


class Escalations(Protocol):
    """The append-only sink the Comment pass owns, typed structurally.

    Deliberately *not* named ``EscalationSink``: that name is taken by the pass's
    concrete class in :mod:`agent.comment_pass`, and two different objects sharing
    one name across a package is how a reader ends up holding the wrong one. The
    pass's class satisfies this Protocol, and the writer never imports the pass.
    """

    def append(
        self,
        *,
        when: datetime,
        platform: str,
        post: str,
        identity: str,
        text: str,
        outcome: Outcome,
        detail: str,
    ) -> None: ...


@dataclass(frozen=True)
class WriteResult:
    """What the write path did for one Comment.

    ``wrote`` is true only after a submit that read back as a Confirmation: a
    write whose result is not known is not a success. ``submitted`` means a submit
    was *attempted*, so the Comment may carry a Reply -- which is why an Unknown
    outcome sets it even when the attempt itself raised. ``outcome`` is ``None``
    when there was nothing to do because the Comment was already handled.
    """

    identity: str
    outcome: Outcome | None
    submitted: bool = False
    wrote: bool = False
    escalated: bool = False
    detail: str = ""


class CommentWriter:
    """One Comment's write: guard the identifier, submit, read the Confirmation.

    The writer is the mechanism only. It carries no cap, no pacing and no kill
    switch (that is #11) and it is not called from anywhere (that is Graduation).
    """

    def __init__(
        self,
        *,
        account: str,
        page: WritePage,
        store: CommentStore,
        escalations: Escalations,
        now=None,
    ) -> None:
        self.account = account
        self.page = page
        self.store = store
        self.escalations = escalations
        self._now = now or (lambda: datetime.now(timezone.utc))

    def write_reply(self, comment: HeldComment, phrasing: Phrasing) -> WriteResult:
        # Two questions, and neither of them is "is there a row?". The pass records
        # a Verdict for every Comment it decides -- CANNED_REPLY included, because
        # the record is the decision and outcomes are insert-only -- so by the time
        # the writer is asked to post, the row normally exists already. Answering
        # "is there a row?" would report every Comment the pass decided to reply to
        # as already handled, which is how a write path ends up posting nothing at
        # all. What matters is (1) whether a Reply is already recorded under this
        # Comment, and (2) whether the Comment was resolved *without* one, meaning
        # its Verdict is something other than the CANNED_REPLY this write realises.
        # ADR 0008: two facts, never one handled flag.
        try:
            prior = self.store.get(comment.platform, comment.identity)
        except CommentNotFound:
            prior = None
        if prior is not None:
            if prior.reply_status is not ReplyStatus.UNKNOWN:
                # The Replied set, in its own field, keyed on the identifier
                # (ADR 0007) -- so a Comment already answered is never posted to
                # again, including one whose text was edited after it was read.
                # This is where AC 3 lives: not in a text comparison here.
                return WriteResult(
                    identity=comment.identity,
                    outcome=None,
                    detail="a Reply is already recorded as "
                    f"{prior.reply_status.name}",
                )
            if prior.outcome is not Outcome.CANNED_REPLY:
                return WriteResult(
                    identity=comment.identity,
                    outcome=None,
                    detail=f"already resolved as {prior.outcome.name}; nothing to post",
                )

        # Bar 4. Re-find and require the identifier the page now shows to equal the
        # one held. The text is never a fallback: an identifier that differs or
        # cannot be read is an Escalation, full stop.
        try:
            read_identity = self.page.re_read_identifier(comment)
        except IdentifierUnreadable as exc:
            return self._escalate(
                comment,
                Outcome.UNCONFIRMED_IDENTIFIER,
                f"identifier unreadable at write time: {exc}",
            )
        if read_identity != comment.identity:
            return self._escalate(
                comment,
                Outcome.UNCONFIRMED_IDENTIFIER,
                "identifier changed from "
                f"{comment.identity!r} to {read_identity!r}; not written",
            )

        # Everything from the submit onward sits inside one guard, and it is caught
        # broadly on purpose. A failure here cannot tell us whether the Reply
        # landed: the click may have registered before the page threw, and the
        # read-back may be the thing that broke. Letting the exception out would
        # leave no record and no Escalation -- and an untouched Replied set means a
        # later run would try this Comment again and could post it a second time,
        # which ADR 0019 calls "the largest correctness risk in this project". So a
        # failure after a submit is recorded as an Unknown outcome and Escalated,
        # never retried; the detail carries the exception so a real bug is still
        # legible in the sink rather than swallowed. Before the submit the opposite
        # holds -- nothing can have posted -- so a failure that is not the page's
        # declared IdentifierUnreadable propagates (the guard above).
        try:
            self.page.submit_reply(comment, phrasing.text)
            confirmation = self.page.read_confirmation(comment)
        except Exception as exc:
            return self._escalate(
                comment,
                Outcome.UNKNOWN_OUTCOME,
                "the submit or the read-back raised, so whether it posted is "
                f"unknown: {exc!r}",
                submitted=True,
                phrasing=phrasing,
            )
        if not self._confirms(confirmation, comment.identity):
            # A submitted write whose Confirmation does not read back is neither
            # posted nor not-posted: an Unknown outcome, Escalated loudly and left
            # to Reconciliation (never retried).
            return self._escalate(
                comment,
                Outcome.UNKNOWN_OUTCOME,
                "submitted but not confirmed against "
                f"{comment.identity!r}: {_describe(confirmation, self.account)}",
                submitted=True,
                phrasing=phrasing,
            )

        if prior is None:
            self.store.record(
                CommentRecord(
                    platform=comment.platform,
                    identity=comment.identity,
                    text=comment.text,
                    baseline=False,
                    outcome=Outcome.CANNED_REPLY,
                    reply_status=ReplyStatus.ANSWERED_BY_ACCOUNT,
                )
            )
        else:
            # The pass has already recorded this Comment's Verdict, and carrying
            # that Verdict out is not a second decision. So the row is repaired
            # rather than rewritten: outcomes are insert-only on purpose
            # (agent.record -- "outcomes are insert-only, repair reply_status
            # instead"), and a Comment the pass decided is the normal case here,
            # not the exception. Inserting would raise CommentAlreadyRecorded
            # *after* the Reply had been posted, which is the state no retry may
            # ever clean up.
            self.store.update_reply_status(
                comment.platform,
                comment.identity,
                ReplyStatus.ANSWERED_BY_ACCOUNT,
            )
        return WriteResult(
            identity=comment.identity,
            outcome=Outcome.CANNED_REPLY,
            submitted=True,
            wrote=True,
            detail=f"posted and confirmed as {self.account}",
        )

    def _confirms(self, confirmation: Confirmation | None, identity: str) -> bool:
        """The Reply reads back under the Comment, attributable to the Account."""
        return (
            confirmation is not None
            and confirmation.identity == identity
            and confirmation.account == self.account
        )

    def _escalate(
        self,
        comment: HeldComment,
        outcome: Outcome,
        detail: str,
        *,
        submitted: bool = False,
        phrasing: Phrasing | None = None,
    ) -> WriteResult:
        # Only escalating outcomes reach here; the partition in agent.record keeps
        # that honest, so the append is unconditional. The append is the part a
        # human acts on, so it must not sit behind a store write that can fail: a
        # Comment the pass has already recorded keeps its Verdict (insert-only)
        # and is Escalated all the same. The record and the sink then say different
        # things on purpose -- the record holds what was decided, the sink holds
        # why the write was refused -- which is why a row whose Verdict is
        # non-escalating can still have a sink entry beside it.
        #
        # `phrasing` is passed by the two refusals that follow a submit, and only
        # by them. Those are the entries a human reconciles a possible
        # double-post from -- ADR 0019's "largest correctness risk in this
        # project" -- and they cannot be reconciled without knowing which words
        # may already be on the page. A refusal *before* the submit names no
        # Reply, because nothing can have posted: the asymmetry is the fact, not
        # an oversight.
        if phrasing is not None:
            detail = (
                f"{detail}; the Reply it may have posted is "
                f"{phrasing.reply_id!r} from the {phrasing.set_id!r} set: "
                f"{phrasing.text!r}"
            )
        try:
            self.store.get(comment.platform, comment.identity)
        except CommentNotFound:
            self.store.record(
                CommentRecord(
                    platform=comment.platform,
                    identity=comment.identity,
                    text=comment.text,
                    baseline=False,
                    outcome=outcome,
                )
            )
        self.escalations.append(
            when=_utc(self._now()),
            platform=comment.platform,
            post=comment.post,
            identity=comment.identity,
            text=comment.text,
            outcome=outcome,
            detail=detail,
        )
        return WriteResult(
            identity=comment.identity,
            outcome=outcome,
            submitted=submitted,
            wrote=False,
            escalated=True,
            detail=detail,
        )


def _describe(confirmation: Confirmation | None, account: str) -> str:
    if confirmation is None:
        return f"no Reply by {account!r} was found under it"
    return (
        f"a Reply reads back as {confirmation.account!r} under "
        f"{confirmation.identity!r}, not as {account!r}"
    )


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
