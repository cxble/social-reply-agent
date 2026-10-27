"""Durable life cycle for Posts the agent has noticed.

ADR 0010 separates two decisions that share a boundary: the Discovery window
decides what may be *newly noticed*, while tracking decides what remains
*watched*. A Tracked post therefore has its own durable record rather than its
scope being re-derived from its age on every pass.

The store uses the same sqlite file as the account's Comment record. That keeps
both kinds of account state behind ``record.store_path`` rather than creating a
second state location.
"""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path


class PostState(Enum):
    NOTICED = "noticed"
    TRACKED = "tracked"
    CLOSED = "closed"


@dataclass(frozen=True)
class TrackedPost:
    platform: str
    post: str
    state: PostState
    noticed_at: datetime
    tracked_at: datetime | None
    closed_at: datetime | None


class TrackedPostStore:
    """Read and write the noticed -> tracked -> closed life cycle."""

    def __init__(self, path: str | Path, account: str):
        self.path = str(path)
        self.account = account
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.path)
        self._connection.executescript(_SCHEMA)
        self._connection.commit()
        os.chmod(self.path, 0o600)

    def close(self) -> None:
        self._connection.close()

    def notice(self, platform: str, post: str, *, when: datetime) -> None:
        """Record first notice once; a closed Post is not re-noticed."""
        self._connection.execute(
            "INSERT OR IGNORE INTO tracked_posts"
            " (platform, post, state, noticed_at, tracked_at, closed_at)"
            " VALUES (?, ?, ?, ?, NULL, NULL)",
            (platform, post, PostState.NOTICED.name, _iso(when)),
        )
        self._connection.commit()

    def track(self, platform: str, post: str, *, when: datetime) -> None:
        """Keep watching a Post that was noticed, unless it has been closed."""
        self.notice(platform, post, when=when)
        self._connection.execute(
            "UPDATE tracked_posts SET state = ?, tracked_at = ?"
            " WHERE platform = ? AND post = ? AND state != ?",
            (
                PostState.TRACKED.name,
                _iso(when),
                platform,
                post,
                PostState.CLOSED.name,
            ),
        )
        self._connection.commit()

    def close_post(self, platform: str, post: str, *, when: datetime) -> None:
        """Close a Post without deleting its history."""
        self.notice(platform, post, when=when)
        self._connection.execute(
            "UPDATE tracked_posts SET state = ?, closed_at = ?"
            " WHERE platform = ? AND post = ?",
            (PostState.CLOSED.name, _iso(when), platform, post),
        )
        self._connection.commit()

    def is_tracked(self, platform: str, post: str) -> bool:
        return self.state(platform, post) is PostState.TRACKED

    def state(self, platform: str, post: str) -> PostState | None:
        row = self._connection.execute(
            "SELECT state FROM tracked_posts WHERE platform = ? AND post = ?",
            (platform, post),
        ).fetchone()
        return None if row is None else PostState[row[0]]

    def get(self, platform: str, post: str) -> TrackedPost | None:
        row = self._connection.execute(
            "SELECT platform, post, state, noticed_at, tracked_at, closed_at"
            " FROM tracked_posts WHERE platform = ? AND post = ?",
            (platform, post),
        ).fetchone()
        if row is None:
            return None
        return TrackedPost(
            platform=row[0],
            post=row[1],
            state=PostState[row[2]],
            noticed_at=datetime.fromisoformat(row[3]),
            tracked_at=None if row[4] is None else datetime.fromisoformat(row[4]),
            closed_at=None if row[5] is None else datetime.fromisoformat(row[5]),
        )


def _iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


_SCHEMA = """
CREATE TABLE IF NOT EXISTS tracked_posts (
    platform TEXT NOT NULL,
    post TEXT NOT NULL,
    state TEXT NOT NULL,
    noticed_at TEXT NOT NULL,
    tracked_at TEXT,
    closed_at TEXT,
    PRIMARY KEY (platform, post)
);
"""
