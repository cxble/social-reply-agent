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

# Whether the Account holder's approval covers this entry's text. Approval only:
# the sign-off record records approval as a decision taken on a date, so there is
# nothing between approved and not-approved for this field to carry.
# `approved` -- the text is signed off and may be posted.
# `escalate` -- no text at all; the entry exists only to route the Intent to a
#   human, and `approved_phrasings` is empty by design.
#
# How sure the matcher must be before posting is a different question, with its own
# answer (`minimum_match_threshold`, tiered by ADR 0019) -- and how far those
# numbers can be trusted is a third. The document says once, for the whole table,
# that the numbers are provisional because they are claims about a Router that does
# not exist in this repository. Neither is approval, so neither is recorded here.
STATUSES = ("approved", "escalate")


class UnknownReplyId(KeyError):
    """A Router supplied a reply id that is not in the loaded reply table.

    Defined here rather than in `matching.py` because this is where the lookup
    that fails lives: `matching.py` imports this module, so an exception defined
    the other way round would have to be imported inside the method body.
    """


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
        raise UnknownReplyId(reply_id)


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
    # D7 -- the 0.50 Floor governs *posting*, so it binds exactly the entries that
    # can post. ADR 0019's floor row says "every entry, any tier" while the same
    # ADR's escalation-gate tier sets 0.20, and `tt-join-001` sits at 0.20 today.
    # Both cannot hold literally; they are resolved on the floor's own reason,
    # which is a posting failure: below 0.50 "an entry is eligible on a reading
    # the Router itself thinks likelier wrong than right, and with 61.1% of the
    # corpus needing no reply that is exactly how a non-sequitur gets posted". An
    # `escalate` entry holds no text at all (ADR 0014: there is no text the agent
    # is permitted to post) and its number is the deliberately lower help
    # threshold, set to catch rather than to be precise -- so the floor does not
    # bind it. This is the one place where the two ADRs cannot both be read
    # literally, and the resolution is a decision, not a detail.
    if item["status"] == "approved" and float(item["minimum_match_threshold"]) < 0.50:
        raise ValueError(
            f"approved entry {item['reply_id']!r} sits at "
            f"minimum_match_threshold={item['minimum_match_threshold']!r}, below the "
            "0.50 floor. ADR 0019 sets the floor because below it an entry is eligible "
            "on a reading the Router thinks likelier wrong than right, and with 61.1% "
            "of the corpus needing no reply that is how a non-sequitur gets posted -- a "
            "posting failure. The floor governs posting, so it does not bind an "
            "`escalate` entry, which holds no text and sits at the deliberately lower "
            "help threshold (ADR 0014)."
        )
