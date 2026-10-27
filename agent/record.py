"""Durable per-Comment records, keyed on the Platform's own identifier.

The key is the Platform's identifier, stored as opaque text, because a hash of
the text would turn an edited Comment into a new one and invite a second Reply
(ADR 0007). Because the key is the durable record, its shape is effectively
permanent: changing it orphans every record behind it. That is written into
the database next to its schema version, so a future migration can read the
version and detect the shape it is looking at before it can quietly lose that
history.

Baseline membership and reply status are two facts, never one handled flag
(ADR 0008): a Comment from before the agent was activated may be recorded
without being eligible for a Reply, and an absent Reply is evidence of nothing.
An absent Reply is recorded as ``ReplyStatus.UNKNOWN``, the third value the
glossary names, and never coerced into a "not answered" fact. Every outcome is
recorded, including those that post nothing.

What the **agent did** is the record (ADR 0008). An outcome is written once and
never rewritten by a later pass, so a recorded ``CANNED_REPLY`` cannot be
quietly downgraded; what the **page shows** is ``reply_status``, which
Reconciliation repairs on its own without re-deciding the Comment.
"""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class CommentNotFound(KeyError):
    """No record exists for that Platform identifier.

    Subclasses ``KeyError`` so a caller that already caught one keeps working,
    but names the failure so it can be told apart from other lookups.
    """


class CommentAlreadyRecorded(RuntimeError):
    """An outcome is already recorded for that Comment and is not rewritten.

    The record captures what the agent decided. A second decision for the same
    Comment is a bug upstream, not an update; Reconciliation repairs
    ``reply_status`` instead, through ``update_reply_status``.
    """


class Outcome(Enum):
    """Why a Comment was not replied to, or that it was.

    The member name is the stable identifier written to the database; the value
    is display wording and may be reworded without making a stored row
    unreadable.
    """

    CANNED_REPLY = "canned reply"
    NO_REPLY = "NO_REPLY"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    BELOW_MINIMUM_MATCH_THRESHOLD = "below minimum_match_threshold"
    UNCERTAIN = "UNCERTAIN"
    CONFLICTING_INTENTS = "conflicting intents"
    UNCONFIRMED_IDENTIFIER = "identifier unconfirmed at write time"
    ESCALATION_GATED_INTENT = "escalation-gated intent"


class ReplyStatus(Enum):
    """What the page shows about whether a Comment has been answered.

    Like ``Outcome``, the member name is written and the value is display
    wording. ``UNKNOWN`` is the value for a Comment with no Reply visible: an
    absent Reply is evidence of nothing (ADR 0008).
    """

    ANSWERED_BY_ACCOUNT = "answered by the Account"
    ANSWERED_BY_SOMEONE_ELSE = "answered by someone else"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class CommentRecord:
    """One Comment's durable record, keyed on the Platform's identifier."""

    platform: str
    identity: str
    text: str
    baseline: bool
    outcome: Outcome
    reply_status: ReplyStatus = ReplyStatus.UNKNOWN


def store_path(account: str) -> Path:
    """Where an account's Comment record lives.

    Uses the same state directory as ``pw_session.state_path`` so the record
    lands alongside the account's other durable state rather than wherever a
    caller happened to be. ``CommentStore`` still takes an explicit ``path``,
    so tests and tools can point it at a temporary file.
    """
    from pw_session import STATE_ROOT

    STATE_ROOT.mkdir(parents=True, exist_ok=True)
    return STATE_ROOT / f"{account}.sqlite3"


class CommentStore:
    """Owns one sqlite3 file per account; records survive a restart.

    Deliberately not a frozen dataclass: it holds a live connection and mutates
    a file, so it is a resource to open and close, not a value to compare.
    """

    def __init__(self, path: str | Path, account: str):
        self.path = str(path)
        self.account = account
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.path)
        self._connection.executescript(_SCHEMA)
        self._connection.commit()
        os.chmod(self.path, 0o600)

    def close(self) -> None:
        """Release the connection. The file stays on disk."""
        self._connection.close()

    def record(self, record: CommentRecord) -> None:
        """Write a Comment's outcome, once.

        Insert-only. A second outcome for the same Comment is refused rather
        than overwriting the first, because the first is what the agent did
        (ADR 0008). Repair ``reply_status`` through ``update_reply_status``.
        """
        try:
            self._connection.execute(
                "INSERT INTO comments"
                " (platform, identity, text, baseline, reply_status, outcome)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (
                    record.platform,
                    record.identity,
                    record.text,
                    int(record.baseline),
                    record.reply_status.name,
                    record.outcome.name,
                ),
            )
        except sqlite3.IntegrityError as exc:
            # Only a primary-key clash means "already recorded". Any other
            # constraint failure is a caller's bug, and reporting it as an
            # already-recorded Comment would be false -- on an empty store there
            # is nothing recorded to have clashed with.
            if not self.contains(record.platform, record.identity):
                raise
            raise CommentAlreadyRecorded(
                f"{record.platform} comment {record.identity} is already recorded;"
                " outcomes are insert-only, repair reply_status instead"
            ) from exc
        self._connection.commit()

    def update_reply_status(
        self, platform: str, identity: str, reply_status: ReplyStatus
    ) -> None:
        """Repair what the page shows about one Comment, without re-deciding it.

        Safe to call repeatedly: Reconciliation runs after the fact and may
        find a different status than the pass that recorded the Comment.
        """
        cursor = self._connection.execute(
            "UPDATE comments SET reply_status = ? WHERE platform = ? AND identity = ?",
            (reply_status.name, platform, identity),
        )
        self._connection.commit()
        if cursor.rowcount == 0:
            raise CommentNotFound((platform, identity))

    def get(self, platform: str, identity: str) -> CommentRecord:
        row = self._connection.execute(
            "SELECT platform, identity, text, baseline, reply_status, outcome"
            " FROM comments WHERE platform = ? AND identity = ?",
            (platform, identity),
        ).fetchone()
        if row is None:
            raise CommentNotFound((platform, identity))
        return CommentRecord(
            platform=row[0],
            identity=row[1],
            text=row[2],
            baseline=bool(row[3]),
            reply_status=ReplyStatus[row[4]],
            outcome=Outcome[row[5]],
        )

    def contains(self, platform: str, identity: str) -> bool:
        return self._connection.execute(
            "SELECT 1 FROM comments WHERE platform = ? AND identity = ? LIMIT 1",
            (platform, identity),
        ).fetchone() is not None

    def schema_version(self) -> int:
        """The stored schema version, for a future migration to branch on."""
        row = self._connection.execute(
            "SELECT value FROM meta WHERE key = 'schema_version'"
        ).fetchone()
        if row is None:
            # Not a CommentNotFound: that means "no record for that Platform
            # identifier", and a caller catching it must not catch this. A
            # missing version means the file is not one of ours.
            raise RuntimeError(f"no schema_version row in {self.path}")
        return int(row[0])

    def schema_text(self) -> str:
        sql = self._connection.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'comments'"
        ).fetchone()[0]
        return sql


_SCHEMA = """
CREATE TABLE IF NOT EXISTS comments (
    -- The key shape is effectively permanent: changing it orphans every
    -- record behind it (ADR 0007). outcome and reply_status store enum member
    -- *names*, not display wording, so rewording a message cannot make an
    -- existing row unreadable.
    platform TEXT NOT NULL,
    identity TEXT NOT NULL,
    text TEXT NOT NULL,
    baseline INTEGER NOT NULL,
    reply_status TEXT NOT NULL,
    outcome TEXT NOT NULL,
    PRIMARY KEY (platform, identity)
);
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
INSERT OR IGNORE INTO meta (key, value) VALUES ('schema_version', '1');
"""
