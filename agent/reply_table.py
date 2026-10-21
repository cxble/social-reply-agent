"""Reply table loading from version-controlled JSON."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_REPLY_TABLE_FIELDS = (
    "reply_id",
    "language",
    "intent",
    "status",
    "approved_phrasings",
    "matching_criteria",
    "known_variants",
    "minimum_match_threshold",
)

# How far the Account holder's approval of this entry's text extends.
# `approved` -- the text is signed off and may be posted.
# `provisional` -- the text is signed off for now, but the entry is named in the
#   document as still under review; it may be posted, and must be revisited.
# `escalate` -- no text at all; the entry exists only to route the Intent to a
#   human, and `approved_phrasings` is empty by design.
STATUSES = ("approved", "provisional", "escalate")


@dataclass(frozen=True)
class ReplyTableEntry:
    reply_id: str
    language: str
    intent: str
    status: str
    approved_phrasings: tuple[str, ...]
    matching_criteria: str
    known_variants: tuple[str, ...]
    minimum_match_threshold: float


@dataclass(frozen=True)
class ReplyTable:
    entries: tuple[ReplyTableEntry, ...]

    def by_reply_id(self, reply_id: str) -> ReplyTableEntry:
        for entry in self.entries:
            if entry.reply_id == reply_id:
                return entry
        raise KeyError(reply_id)


def reply_table_path(name: str = "tiktok") -> Path:
    return Path(__file__).resolve().parent.parent / "reply-tables" / f"{name}.json"


def load_reply_table(name: str = "tiktok") -> ReplyTable:
    data = json.loads(reply_table_path(name).read_text())
    entries = []
    for item in data:
        _validate_entry(item)
        entries.append(
            ReplyTableEntry(
                reply_id=item["reply_id"],
                language=item["language"],
                intent=item["intent"],
                status=item["status"],
                approved_phrasings=tuple(item["approved_phrasings"]),
                matching_criteria=item["matching_criteria"],
                known_variants=tuple(item["known_variants"]),
                minimum_match_threshold=float(item["minimum_match_threshold"]),
            )
        )
    return ReplyTable(entries=tuple(entries))


def _validate_entry(item: dict[str, Any]) -> None:
    missing = [field for field in _REPLY_TABLE_FIELDS if field not in item]
    if missing:
        raise ValueError(f"missing fields {missing} in {item!r}")
    if item["status"] not in STATUSES:
        raise ValueError(f"unknown status {item['status']!r} in {item['reply_id']!r}")
    if item["status"] == "escalate" and item["approved_phrasings"]:
        raise ValueError(f"escalation-only entry {item['reply_id']!r} carries postable text")
