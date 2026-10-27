"""Tests for the durable Comment record and Replied set.

Each test maps to one acceptance criterion of ticket 3. The restart tests open a
second store over the same file while the first is still open, and the ones that
close it first say so — either way the second store is a real second connection
over the same bytes, not in-memory state being consulted twice.
"""

import sqlite3
from pathlib import Path

import pytest

from agent.record import (
    ESCALATING_OUTCOMES,
    CommentAlreadyRecorded,
    CommentNotFound,
    CommentRecord,
    CommentStore,
    NON_ESCALATING_OUTCOMES,
    Outcome,
    ReplyStatus,
    escalates,
    store_path,
)


def _record(
    identity: str,
    *,
    text: str = "unchanged text",
    platform: str = "tiktok",
    baseline: bool = False,
    outcome: Outcome = Outcome.NO_REPLY,
    reply_status: ReplyStatus | None = None,
) -> CommentRecord:
    kwargs = {} if reply_status is None else {"reply_status": reply_status}
    return CommentRecord(
        platform=platform,
        identity=identity,
        text=text,
        baseline=baseline,
        outcome=outcome,
        **kwargs,
    )


@pytest.fixture
def store(tmp_path):
    s = CommentStore(tmp_path / "acct.sqlite3", account="acct")
    yield s
    s.close()


# --- A: the Replied set keys on the Platform's identifier, never the text -----


def test_identical_text_under_different_identities_are_two_records(store):
    # Two Comments that read the same are two Comments: the Platform gave them
    # different identifiers, so the Replied set holds both and neither suppresses
    # the other (ADR 0007).
    store.record(_record("7201", text="alhamdulillah"))
    store.record(_record("7202", text="alhamdulillah"))

    assert store.contains("tiktok", "7201")
    assert store.contains("tiktok", "7202")
    assert store.get("tiktok", "7201").identity == "7201"
    assert store.get("tiktok", "7202").identity == "7202"


def test_editing_a_comment_does_not_make_it_a_new_one(store):
    # One Comment, one identifier, edited text. Because the key is the identifier
    # and not a hash of the text, the edit does not make it a new Comment: it is
    # already in the Replied set and cannot be answered a second time (ADR 0007).
    store.record(_record("7210", text="original words", outcome=Outcome.CANNED_REPLY))

    assert store.contains("tiktok", "7210")

    # A later pass reads the same identifier with the edited text. Recording it
    # as new is refused, and the first record is left untouched.
    with pytest.raises(CommentAlreadyRecorded):
        store.record(_record("7210", text="edited words", outcome=Outcome.CANNED_REPLY))

    assert store.get("tiktok", "7210").text == "original words"


# --- B: Baseline membership and Reply status are independent facts ------------


def test_baseline_and_reply_status_are_independent(store):
    # All four combinations of (baseline, answered / not answered) round-trip,
    # each on its own Comment, without either field implying the other (ADR 0008).
    combinations = [
        (True, ReplyStatus.ANSWERED_BY_ACCOUNT),
        (True, ReplyStatus.UNKNOWN),
        (False, ReplyStatus.ANSWERED_BY_ACCOUNT),
        (False, ReplyStatus.UNKNOWN),
    ]
    for index, (baseline, reply_status) in enumerate(combinations):
        store.record(
            _record(str(index), baseline=baseline, reply_status=reply_status)
        )

    for index, (baseline, reply_status) in enumerate(combinations):
        record = store.get("tiktok", str(index))
        assert record.baseline is baseline
        assert record.reply_status is reply_status


def test_a_comment_with_no_reply_on_the_page_is_unknown(store):
    # ADR 0008: an absent Reply is evidence of nothing. It is stored as
    # `unknown`, not coerced into a "not answered" fact.
    store.record(_record("7211", outcome=Outcome.NO_REPLY))
    assert store.get("tiktok", "7211").reply_status is ReplyStatus.UNKNOWN


# --- AC 2: the record still says why a Comment was skipped, after a restart ---


def test_skip_reason_survives_restart(tmp_path):
    path = tmp_path / "acct.sqlite3"
    first = CommentStore(path, account="acct")
    first.record(_record("7202", outcome=Outcome.UNCERTAIN))
    first.close()

    reopened = CommentStore(path, account="acct")
    try:
        assert reopened.get("tiktok", "7202").outcome is Outcome.UNCERTAIN
    finally:
        reopened.close()


# --- AC 3: nothing is answered twice, across a restart ------------------------


def test_replied_comment_not_answered_again_across_restart(tmp_path):
    path = tmp_path / "acct.sqlite3"
    first = CommentStore(path, account="acct")
    first.record(
        _record(
            "7203",
            outcome=Outcome.CANNED_REPLY,
            reply_status=ReplyStatus.ANSWERED_BY_ACCOUNT,
        )
    )
    first.close()

    reopened = CommentStore(path, account="acct")
    try:
        assert reopened.contains("tiktok", "7203")
    finally:
        reopened.close()


# --- C: enum values are stored as stable names, not display wording -----------


def test_stored_enum_values_are_stable_names_not_display_wording(store):
    store.record(
        _record("7301", outcome=Outcome.BELOW_MINIMUM_MATCH_THRESHOLD)
    )
    store.record(
        _record(
            "7302",
            outcome=Outcome.CANNED_REPLY,
            reply_status=ReplyStatus.ANSWERED_BY_ACCOUNT,
        )
    )

    with sqlite3.connect(store.path) as conn:
        stored = dict(conn.execute("SELECT identity, outcome FROM comments"))

    assert stored["7301"] == "BELOW_MINIMUM_MATCH_THRESHOLD"
    assert stored["7302"] == "CANNED_REPLY"
    # The display wording is kept as the enum's value, separate from what is
    # written, so rewording it later cannot make a stored row unreadable.
    assert (
        Outcome.BELOW_MINIMUM_MATCH_THRESHOLD.value == "below minimum_match_threshold"
    )


# --- D: the schema version is readable, so a migration can detect the shape ---


def test_schema_version_is_readable_after_restart(tmp_path):
    path = tmp_path / "acct.sqlite3"
    first = CommentStore(path, account="acct")
    assert first.schema_version() == 1
    first.close()

    reopened = CommentStore(path, account="acct")
    try:
        assert reopened.schema_version() == 1
    finally:
        reopened.close()


def test_a_missing_schema_version_is_not_reported_as_a_missing_comment(store):
    # CommentNotFound means "no record for that Platform identifier". A meta row
    # that is not there is a different failure, and a caller catching
    # CommentNotFound to mean "not in the Replied set" must not be catching this.
    with sqlite3.connect(store.path) as conn:
        conn.execute("DELETE FROM meta WHERE key = 'schema_version'")

    with pytest.raises(RuntimeError) as caught:
        store.schema_version()

    assert not isinstance(caught.value, CommentNotFound)


# --- E: the record file is not world readable --------------------------------


def test_state_file_is_not_world_readable(store):
    mode = Path(store.path).stat().st_mode
    assert mode & 0o077 == 0, f"record file is too permissive: {oct(mode)}"


# --- F: the on-disk location follows the account state convention -------------


def test_store_path_follows_the_account_state_convention():
    from pw_session import STATE_ROOT

    assert store_path("acct") == STATE_ROOT / "acct.sqlite3"
    assert (
        store_path("acct")
        == Path.home() / ".config" / "social-bot" / "state" / "acct.sqlite3"
    )


# --- G: the store closes; the restart tests really open a second connection ---


def test_close_releases_the_connection(tmp_path):
    store = CommentStore(tmp_path / "acct.sqlite3", account="acct")
    store.close()
    with pytest.raises(sqlite3.ProgrammingError):
        store.contains("tiktok", "anything")


# --- H: recording an outcome is insert-only; reply status is repairable -------


def test_a_second_outcome_is_refused_and_does_not_overwrite(store):
    store.record(_record("7401", outcome=Outcome.CANNED_REPLY))

    with pytest.raises(CommentAlreadyRecorded):
        store.record(_record("7401", outcome=Outcome.NO_REPLY))

    assert store.get("tiktok", "7401").outcome is Outcome.CANNED_REPLY


def test_a_constraint_failure_is_not_dressed_up_as_already_recorded(store):
    # `record()` translates a primary-key clash into CommentAlreadyRecorded. Any
    # other IntegrityError is a caller's bug and must stay one: on an empty store
    # the "already recorded" message is simply false. Here a NULL text violates
    # NOT NULL, which is nothing to do with a second outcome.
    assert not store.contains("tiktok", "never-recorded")

    with pytest.raises(sqlite3.IntegrityError) as caught:
        store.record(_record("never-recorded", text=None))

    assert not isinstance(caught.value, CommentAlreadyRecorded)
    assert not store.contains("tiktok", "never-recorded")


def test_reply_status_can_be_repaired_repeatedly_without_touching_the_outcome(store):
    store.record(
        _record(
            "7402",
            outcome=Outcome.CANNED_REPLY,
            reply_status=ReplyStatus.UNKNOWN,
        )
    )

    store.update_reply_status("tiktok", "7402", ReplyStatus.ANSWERED_BY_ACCOUNT)
    assert (
        store.get("tiktok", "7402").reply_status is ReplyStatus.ANSWERED_BY_ACCOUNT
    )

    # Reconciliation may run again; the outcome is never re-decided.
    store.update_reply_status(
        "tiktok", "7402", ReplyStatus.ANSWERED_BY_SOMEONE_ELSE
    )
    record = store.get("tiktok", "7402")
    assert record.reply_status is ReplyStatus.ANSWERED_BY_SOMEONE_ELSE
    assert record.outcome is Outcome.CANNED_REPLY


# --- J: a missing record raises a named error, not a bare KeyError ------------


def test_get_names_the_missing_record(store):
    with pytest.raises(CommentNotFound):
        store.get("tiktok", "not-recorded")


def test_update_reply_status_names_a_missing_record(store):
    with pytest.raises(CommentNotFound):
        store.update_reply_status("tiktok", "not-recorded", ReplyStatus.UNKNOWN)


# --- K: every Outcome has a hand-decided escalation verdict (D1) --------------


def test_outcome_partition_is_total_and_disjoint():
    # The partition is the whole decision of who is shown a Comment. Adding a
    # ninth Outcome fails this test until someone decides, in writing, whether a
    # human sees it -- a default would let a new outcome go silent by omission,
    # which is the failure ADR 0018 forbids.
    assert ESCALATING_OUTCOMES.isdisjoint(NON_ESCALATING_OUTCOMES)
    assert ESCALATING_OUTCOMES | NON_ESCALATING_OUTCOMES == set(Outcome)


def test_every_outcome_has_the_verdict_the_record_assigns_it():
    assert ESCALATING_OUTCOMES == {
        Outcome.OUT_OF_SCOPE,
        Outcome.BELOW_MINIMUM_MATCH_THRESHOLD,
        Outcome.CONFLICTING_INTENTS,
        Outcome.UNCERTAIN,
        Outcome.ESCALATION_GATED_INTENT,
        Outcome.UNCONFIRMED_IDENTIFIER,
    }
    assert NON_ESCALATING_OUTCOMES == {Outcome.CANNED_REPLY, Outcome.NO_REPLY}
    for outcome in ESCALATING_OUTCOMES:
        assert escalates(outcome) is True, outcome
    for outcome in NON_ESCALATING_OUTCOMES:
        assert escalates(outcome) is False, outcome
