from __future__ import annotations

import inspect
import json
import stat
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from agent.adapters.tiktok import PostComments, TikTokRecordedPageAdapter, TruncatedRead
from agent.comment_pass import (
    CommentPass,
    DryRunViolation,
    EscalationSink,
    MissingBaseline,
    PostPage,
    PostPageUnavailable,
    SessionDead,
    escalation_path,
    submit_reply,
)
from agent.record import CommentRecord, CommentStore, Outcome
from agent.reply_table import load_reply_table
from agent.tracked_posts import PostState, TrackedPostStore

FIXTURES = Path(__file__).parent / "fixtures" / "recorded"
PASS_PAGE = FIXTURES / "tiktok_pass.html"
NOW = datetime(2026, 10, 28, 12, 0, tzinfo=timezone.utc)


@dataclass
class DecisionsDouble:
    reply_id: str | None = None
    call_count: int = 0
    seen: list[str] = field(default_factory=list)
    forbidden: bool = False

    def decide(self, normalized_comment: str) -> str | None:
        self.call_count += 1
        self.seen.append(normalized_comment)
        if self.forbidden:
            raise AssertionError("the Replied set must be checked before deciding")
        return self.reply_id


class ReaderDouble:
    def __init__(self, results):
        self.results = results
        self.paths: list[Path] = []

    def read_comments(self, path):
        self.paths.append(Path(path))
        result = self.results[Path(path)]
        if isinstance(result, Exception):
            raise result
        return result


@pytest.fixture
def store(tmp_path):
    s = CommentStore(tmp_path / "acct.sqlite3", account="acct")
    yield s
    s.close()


@pytest.fixture
def tracker(store):
    t = TrackedPostStore(store.path, account=store.account)
    yield t
    t.close()


def _pass(store, tracker, tmp_path, *, reader=None, baseline=frozenset(), decisions=None):
    return CommentPass(
        platform="tiktok",
        baseline=baseline,
        reader=reader or TikTokRecordedPageAdapter(),
        reply_table=load_reply_table(),
        decisions_client=decisions or DecisionsDouble("tt-greet-001"),
        store=store,
        tracked_posts=tracker,
        escalations=EscalationSink(tmp_path / "acct.escalations.jsonl"),
        dead_session_marker=tmp_path / "acct.session-dead.json",
        discovery_window=timedelta(days=7),
        now=lambda: NOW,
    )


def test_pass_finds_eligible_comments_decides_records_and_posts_nothing(
    store, tracker, tmp_path
):
    decisions = DecisionsDouble("tt-greet-001")
    pass_ = _pass(
        store,
        tracker,
        tmp_path,
        baseline={"c-base"},
        decisions=decisions,
    )

    report = pass_.run(
        [PostPage(post="p-1", path=PASS_PAGE, created_at=NOW - timedelta(hours=1))]
    )

    assert report.skipped_baseline == ("c-base",)
    assert [record.identity for record in report.recorded] == [
        "c-old",
        "c-mid",
        "c-new",
        "c-missing",
        "c-replied",
    ]
    assert [(record.identity, record.outcome) for record in report.recorded] == [
        ("c-old", Outcome.ESCALATION_GATED_INTENT),
        ("c-mid", Outcome.CANNED_REPLY),
        ("c-new", Outcome.CANNED_REPLY),
        ("c-missing", Outcome.CANNED_REPLY),
        ("c-replied", Outcome.CANNED_REPLY),
    ]
    assert all(record.baseline is False for record in report.recorded)
    assert decisions.call_count == 1
    assert decisions.seen == ["an unmatched but already answered comment"]
    assert store.get("tiktok", "c-old").outcome is Outcome.ESCALATION_GATED_INTENT
    assert len(report.escalations) == 1
    lines = (tmp_path / "acct.escalations.jsonl").read_text().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["identity"] == "c-old"


def test_dry_run_cannot_be_given_a_writer_and_refuses_if_reached():
    # The property is that a Dry-run pass cannot be *handed* anything that
    # writes, not that three particular attribute names are absent -- a
    # `post_comment` or a `session` would satisfy that weaker check. So pin the
    # constructor's parameters: adding a browser, a Page, a Session or a
    # submitter to the pass fails here. That is the guard that keeps Dry run
    # structural rather than a flag someone can pass wrong. A future ticket that
    # adds a parameter has to come through this test and say why it is not a
    # writer.
    assert set(inspect.signature(CommentPass.__init__).parameters) == {
        "self",
        "platform",
        "baseline",
        "reader",
        "reply_table",
        "decisions_client",
        "store",
        "tracked_posts",
        "escalations",
        "dead_session_marker",
        "discovery_window",
        "now",
    }

    with pytest.raises(DryRunViolation, match="Dry run"):
        submit_reply("tiktok", "p-1", "c-1", "never posted")


def test_a_pass_without_an_explicit_baseline_refuses_to_run(
    store, tracker, tmp_path
):
    with pytest.raises(MissingBaseline, match="baseline"):
        CommentPass(
            platform="tiktok",
            baseline=None,
            reader=TikTokRecordedPageAdapter(),
            reply_table=load_reply_table(),
            decisions_client=DecisionsDouble(),
            store=store,
            tracked_posts=tracker,
            escalations=EscalationSink(tmp_path / "acct.escalations.jsonl"),
            dead_session_marker=tmp_path / "acct.session-dead.json",
            now=lambda: NOW,
        )


def test_an_empty_explicit_baseline_is_different_from_omitting_it(
    store, tracker, tmp_path
):
    pass_ = _pass(store, tracker, tmp_path, baseline=frozenset())
    report = pass_.run(
        [PostPage(post="p-1", path=PASS_PAGE, created_at=NOW - timedelta(hours=1))]
    )
    assert "c-base" in [record.identity for record in report.recorded]


def test_a_comment_already_in_the_replied_set_is_never_decided_again(
    store, tracker, tmp_path
):
    store.record(
        CommentRecord(
            platform="tiktok",
            identity="c-replied",
            text="an unmatched but already answered comment",
            baseline=False,
            outcome=Outcome.CANNED_REPLY,
        )
    )
    decisions = DecisionsDouble("tt-greet-001", forbidden=True)
    pass_ = _pass(store, tracker, tmp_path, decisions=decisions)

    report = pass_.run(
        [PostPage(post="p-1", path=PASS_PAGE, created_at=NOW - timedelta(hours=1))]
    )

    assert decisions.call_count == 0
    assert report.skipped_replied == ("c-replied",)
    assert "c-replied" not in [record.identity for record in report.recorded]


def test_escalation_sink_is_append_only_json_lines_with_mode_0600(tmp_path):
    sink = EscalationSink(tmp_path / "acct.escalations.jsonl")
    first = datetime(2026, 10, 28, 1, 2, 3, tzinfo=timezone.utc)
    second = datetime(2026, 10, 28, 1, 2, 4, tzinfo=timezone.utc)

    sink.append(
        when=first,
        platform="tiktok",
        post="p-1",
        identity="c-1",
        text="please help",
        outcome=Outcome.ESCALATION_GATED_INTENT,
        detail="HELP_REQUEST",
    )
    sink.append(
        when=second,
        platform="tiktok",
        post="p-1",
        identity="c-2",
        text="how do I join?",
        outcome=Outcome.ESCALATION_GATED_INTENT,
        detail="JOIN_ENQUIRY via tt-join-001",
    )

    path = tmp_path / "acct.escalations.jsonl"
    lines = path.read_text().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0]) == {
        "when": "2026-10-28T01:02:03+00:00",
        "platform": "tiktok",
        "post": "p-1",
        "identity": "c-1",
        "text": "please help",
        "outcome": "ESCALATION_GATED_INTENT",
        "detail": "HELP_REQUEST",
    }
    assert json.loads(lines[1])["identity"] == "c-2"
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert escalation_path("acct").parent.name == "state"


def test_dead_session_stops_before_deciding_and_leaves_count_evidence(
    store, tracker, tmp_path
):
    reader = ReaderDouble(
        {Path("truncated.html"): TruncatedRead(total=5, read=2)}
    )
    pass_ = _pass(store, tracker, tmp_path, reader=reader)

    with pytest.raises(SessionDead) as caught:
        pass_.run(
            [
                PostPage(
                    post="p-dead",
                    path=Path("truncated.html"),
                    created_at=NOW - timedelta(hours=1),
                )
            ]
        )

    marker = json.loads((tmp_path / "acct.session-dead.json").read_text())
    assert marker["platform"] == "tiktok"
    assert marker["post"] == "p-dead"
    assert marker["read"] == 2
    assert marker["total"] == 5
    assert "read 2" in marker["detail"] and "total 5" in marker["detail"]
    assert caught.value.marker == tmp_path / "acct.session-dead.json"
    assert not any(store.contains("tiktok", identity) for identity in ("c-old", "c-mid"))


def test_a_tracked_post_that_stops_loading_is_closed_without_stopping_the_pass(
    store, tracker, tmp_path
):
    tracker.notice("tiktok", "p-gone", when=NOW - timedelta(days=30))
    tracker.track("tiktok", "p-gone", when=NOW - timedelta(days=30))
    reader = ReaderDouble(
        {
            Path("gone.html"): PostPageUnavailable("the Post is no longer available"),
            Path("live.html"): PostComments(comments=(), total=0),
        }
    )
    pass_ = _pass(store, tracker, tmp_path, reader=reader)

    report = pass_.run(
        [
            PostPage(
                post="p-gone",
                path=Path("gone.html"),
                created_at=NOW - timedelta(days=30),
            ),
            PostPage(
                post="p-live",
                path=Path("live.html"),
                created_at=NOW - timedelta(hours=1),
            ),
        ]
    )

    assert report.closed_posts == ("p-gone",)
    assert tracker.state("tiktok", "p-gone") is PostState.CLOSED
    assert tracker.state("tiktok", "p-live") is PostState.TRACKED


def test_discovery_window_only_gates_new_noticing_while_tracking_keeps_watching(
    store, tracker, tmp_path
):
    tracker.notice("tiktok", "p-old-tracked", when=NOW - timedelta(days=30))
    tracker.track("tiktok", "p-old-tracked", when=NOW - timedelta(days=30))
    reader = ReaderDouble(
        {
            Path("tracked.html"): PostComments(comments=(), total=0),
            Path("new.html"): PostComments(comments=(), total=0),
        }
    )
    pass_ = _pass(store, tracker, tmp_path, reader=reader)

    report = pass_.run(
        [
            PostPage(
                post="p-old-untracked",
                path=Path("old.html"),
                created_at=NOW - timedelta(days=30),
            ),
            PostPage(
                post="p-old-tracked",
                path=Path("tracked.html"),
                created_at=NOW - timedelta(days=30),
            ),
            PostPage(
                post="p-new",
                path=Path("new.html"),
                created_at=NOW - timedelta(hours=1),
            ),
        ]
    )

    assert reader.paths == [Path("tracked.html"), Path("new.html")]
    assert report.skipped_posts == ("p-old-untracked",)
    assert tracker.state("tiktok", "p-old-tracked") is PostState.TRACKED
    assert tracker.state("tiktok", "p-new") is PostState.TRACKED
