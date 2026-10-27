"""The Comment pass walking skeleton: decide and record, never post.

Dry run is structural here. The pass is handed a read-only Comment reader, a
Reply table, a decisions client and durable stores; it is never handed a
browser, Page, Session or submitter. There is no branch that can turn posting
on. The named :func:`submit_reply` sentinel exists only so a path that somehow
reaches a write fails loudly rather than silently doing nothing.

Eligibility requires an explicit Baseline (ADR 0008). It is recorded state
produced by Seeding, not inferred from a missing Reply. A caller that passes
``None`` is refused; an empty set is a valid, explicit Baseline.

Discovery and tracking are deliberately separate (ADR 0010):

* the Discovery window decides which Posts may be newly noticed; and
* the durable Tracked-post record decides which Posts remain watched after they
  age out.

A Tracked post whose page no longer loads is closed and the pass continues. A
Truncated read is different: it is a dead Session, so the pass records the
count evidence in a marker and stops before deciding any Comment.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Collection, Iterable, Protocol

from agent.adapters.tiktok import PostComments, TruncatedRead
from agent.matching import DecisionsClient, Matcher
from agent.read_errors import PostPageUnavailable
from agent.record import CommentRecord, CommentStore, Outcome
from agent.reply_table import ReplyTable
from agent.tracked_posts import PostState, TrackedPostStore


class MissingBaseline(RuntimeError):
    """A Comment pass was started without the recorded Baseline boundary."""


class DryRunViolation(RuntimeError):
    """A write path was reached while the pass is structurally in Dry run."""


class SessionDead(RuntimeError):
    """A Truncated read stopped the Platform agent and left a marker."""

    def __init__(self, marker: Path, detail: str) -> None:
        self.marker = marker
        super().__init__(f"dead Session; marker left at {marker}: {detail}")


class CommentReader(Protocol):
    def read_comments(self, path: str | Path) -> PostComments: ...


@dataclass(frozen=True)
class PostPage:
    post: str
    path: Path
    created_at: datetime | None = None


@dataclass(frozen=True)
class PassReport:
    recorded: tuple[CommentRecord, ...] = ()
    escalations: tuple[CommentRecord, ...] = ()
    skipped_baseline: tuple[str, ...] = ()
    skipped_replied: tuple[str, ...] = ()
    skipped_posts: tuple[str, ...] = ()
    closed_posts: tuple[str, ...] = ()


def submit_reply(*args, **kwargs):
    """Refuse every attempted write; the Comment pass has no submitter."""
    raise DryRunViolation("Dry run refuses to submit anything")


def escalation_path(account: str) -> Path:
    """The account's append-only Escalation sink under the state convention."""
    from pw_session import STATE_ROOT

    STATE_ROOT.mkdir(parents=True, exist_ok=True)
    return STATE_ROOT / f"{account}.escalations.jsonl"


def dead_session_path(account: str) -> Path:
    """The account's dead-Session marker under the state convention."""
    from pw_session import STATE_ROOT

    STATE_ROOT.mkdir(parents=True, exist_ok=True)
    return STATE_ROOT / f"{account}.session-dead.json"


class EscalationSink:
    """Append one person-readable JSON object per Escalation."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

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
    ) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "when": _iso(when),
            "platform": platform,
            "post": post,
            "identity": identity,
            "text": text,
            "outcome": outcome.name,
            "detail": detail,
        }
        descriptor = os.open(
            self.path,
            os.O_WRONLY | os.O_CREAT | os.O_APPEND,
            0o600,
        )
        try:
            os.chmod(self.path, 0o600)
            with os.fdopen(descriptor, "a", encoding="utf-8") as stream:
                descriptor = -1
                stream.write(json.dumps(entry, ensure_ascii=False) + "\n")
        finally:
            if descriptor >= 0:
                os.close(descriptor)


class CommentPass:
    """One sweep over supplied Posts that records decisions in Dry run."""

    def __init__(
        self,
        *,
        platform: str,
        baseline: Collection[str] | None,
        reader: CommentReader,
        reply_table: ReplyTable,
        decisions_client: DecisionsClient,
        store: CommentStore,
        tracked_posts: TrackedPostStore | None = None,
        escalations: EscalationSink | None = None,
        dead_session_marker: str | Path | None = None,
        discovery_window: timedelta = timedelta(days=7),
        now=None,
    ) -> None:
        if baseline is None:
            raise MissingBaseline(
                "the baseline is recorded at activation and must be passed explicitly"
            )
        self.platform = platform
        self.baseline = frozenset(baseline)
        self.reader = reader
        self.matcher = Matcher(reply_table, decisions_client)
        self.store = store
        self.tracked_posts = tracked_posts or TrackedPostStore(
            store.path, account=store.account
        )
        self.escalations = escalations or EscalationSink(escalation_path(store.account))
        self.dead_session_marker = Path(
            dead_session_marker or dead_session_path(store.account)
        )
        self.discovery_window = discovery_window
        self._now = now or (lambda: datetime.now(timezone.utc))

    def run(self, pages: Iterable[PostPage]) -> PassReport:
        now = _utc(self._now())
        readable: list[PostPage] = []
        skipped_posts: list[str] = []
        closed_posts: list[str] = []

        # Phase one is discovery/reading. All reads happen before any decision,
        # so a dead Session on a later Post cannot leave earlier Comments
        # half-decided by this pass.
        for page in pages:
            state = self.tracked_posts.state(self.platform, page.post)
            if state is PostState.CLOSED:
                skipped_posts.append(page.post)
                continue
            if state is PostState.NOTICED:
                # A Post already noticed stays in scope even if it is now aged
                # out; that is the tracking decision, separate from discovery.
                self.tracked_posts.track(self.platform, page.post, when=now)
            elif state is not PostState.TRACKED:
                if not self._inside_discovery_window(page, now):
                    skipped_posts.append(page.post)
                    continue
                self.tracked_posts.notice(self.platform, page.post, when=now)
                self.tracked_posts.track(self.platform, page.post, when=now)
            readable.append(page)

        found: list[tuple[int, PostPage, object]] = []
        discovery_index = 0
        for page in readable:
            try:
                post_comments = self.reader.read_comments(page.path)
            except TruncatedRead as exc:
                marker = self._leave_dead_session_marker(page.post, exc, now)
                raise SessionDead(marker, str(exc)) from exc
            except (PostPageUnavailable, FileNotFoundError) as exc:
                self.tracked_posts.close_post(self.platform, page.post, when=now)
                closed_posts.append(page.post)
                continue

            for comment in post_comments.comments:
                found.append((discovery_index, page, comment))
                discovery_index += 1

        found.sort(key=lambda item: _comment_sort_key(item[2], item[0]))
        recorded: list[CommentRecord] = []
        escalations: list[CommentRecord] = []
        skipped_baseline: list[str] = []
        skipped_replied: list[str] = []

        for _, page, comment in found:
            if comment.identity in self.baseline:
                skipped_baseline.append(comment.identity)
                continue
            if self.store.contains(self.platform, comment.identity):
                # The Replied set is checked before the Router; an already
                # recorded Comment is never decided again (ADR 0007).
                skipped_replied.append(comment.identity)
                continue

            match = self.matcher.match_comment(comment.text)
            entry = match.entry
            if entry is None:
                outcome = Outcome.OUT_OF_SCOPE
                detail = "no Canned reply covers the Comment"
            elif entry.status == "escalate":
                outcome = Outcome.ESCALATION_GATED_INTENT
                detail = f"{entry.intent} via {entry.reply_id}"
            else:
                outcome = Outcome.CANNED_REPLY
                detail = entry.reply_id

            record = CommentRecord(
                platform=self.platform,
                identity=comment.identity,
                text=comment.text,
                baseline=False,
                outcome=outcome,
            )
            self.store.record(record)
            recorded.append(record)

            if outcome is Outcome.ESCALATION_GATED_INTENT:
                escalations.append(record)
                self.escalations.append(
                    when=now,
                    platform=self.platform,
                    post=page.post,
                    identity=comment.identity,
                    text=comment.text,
                    outcome=outcome,
                    detail=detail,
                )

        return PassReport(
            recorded=tuple(recorded),
            escalations=tuple(escalations),
            skipped_baseline=tuple(skipped_baseline),
            skipped_replied=tuple(skipped_replied),
            skipped_posts=tuple(skipped_posts),
            closed_posts=tuple(closed_posts),
        )

    def _inside_discovery_window(self, page: PostPage, now: datetime) -> bool:
        if page.created_at is None:
            # A missing creation time is not evidence that a Post is young.
            return False
        return _utc(page.created_at) >= now - self.discovery_window

    def _leave_dead_session_marker(
        self, post: str, exc: TruncatedRead, now: datetime
    ) -> Path:
        read, total = _truncation_evidence(exc)
        self.dead_session_marker.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "when": _iso(now),
            "platform": self.platform,
            "post": post,
            "read": read,
            "total": total,
            "detail": str(exc),
        }
        temporary = self.dead_session_marker.with_suffix(
            self.dead_session_marker.suffix + ".tmp"
        )
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            os.chmod(temporary, 0o600)
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                descriptor = -1
                json.dump(payload, stream, ensure_ascii=False)
                stream.write("\n")
        finally:
            if descriptor >= 0:
                os.close(descriptor)
        os.replace(temporary, self.dead_session_marker)
        os.chmod(self.dead_session_marker, 0o600)
        return self.dead_session_marker


def _truncation_evidence(exc: TruncatedRead) -> tuple[int | None, int | None]:
    read = getattr(exc, "read", None)
    total = getattr(exc, "total", None)
    if read is None or total is None:
        match = re.search(r"total (\d+), read (\d+)", str(exc))
        if match:
            total = int(match.group(1))
            read = int(match.group(2))
    return read, total


def _comment_sort_key(comment, discovery_index: int):
    """Oldest first; a missing timestamp sorts after known times, stably.

    A missing creation time is not evidence of age (D5). Comments with one are
    ordered by that time in UTC. Comments without one follow in discovery
    order, with their discovery index breaking ties and keeping the sort stable.
    """
    created_at = getattr(comment, "created_at", None)
    if created_at is None:
        return 1, datetime.max.replace(tzinfo=timezone.utc), discovery_index
    return 0, _utc(created_at), discovery_index


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _iso(value: datetime) -> str:
    return _utc(value).isoformat()
