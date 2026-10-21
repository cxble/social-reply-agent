"""Variant matching and normalized-form match cache."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from agent.normalize import normalize
from agent.reply_table import ReplyTable, ReplyTableEntry


class DecisionsClient(Protocol):
    def decide(self, normalized_comment: str) -> str | None: ...


@dataclass(frozen=True)
class MatchResult:
    entry: ReplyTableEntry | None
    normalized_comment: str


# Which entry owns a normalized Comment that meets a Variant in more than one.
#
# The approval record files two of these Comments under both `DOA_BLESSING` and
# `PRAISE_ENCOURAGE`, because one sentence can praise a person and ask Allah for
# their recovery at once. The overlap cannot be taken out of the record without
# dropping a real Comment, so what is decided here is which entry answers it -- and
# it is decided by declaration rather than by file order. The alternative is that
# whichever entry comes later in `reply-tables/tiktok.json` wins, so reordering a
# data file would silently change what the agent posts.
#
# Earlier in this tuple wins. `tt-doa-002` wins its overlap on the record's own
# criteria: `tt-praise-001` is "praise or encouragement with no request and no
# explicit doa", and both overlapping Comments carry an explicit doa, so the praise
# entry's own definition excludes them.
VARIANT_PRECEDENCE = ("tt-doa-001", "tt-doa-002", "tt-doareq-001")


def _resolve_variant_conflict(
    key: str, first: ReplyTableEntry, second: ReplyTableEntry
) -> ReplyTableEntry:
    """Choose between two entries that both claim the same normalized Comment."""
    ranked = [entry for entry in (first, second) if entry.reply_id in VARIANT_PRECEDENCE]
    if not ranked:
        raise ValueError(
            f"the variant {key!r} is carried by both {first.reply_id!r} and "
            f"{second.reply_id!r}, and which of them answers it is not declared. Add "
            "the winning entry to VARIANT_PRECEDENCE; do not let the order of the "
            "reply table decide it."
        )
    return min(ranked, key=lambda entry: VARIANT_PRECEDENCE.index(entry.reply_id))


class Matcher:
    def __init__(self, reply_table: ReplyTable, decisions_client: DecisionsClient) -> None:
        self._reply_table = reply_table
        self._decisions_client = decisions_client
        self._variant_index = self._build_variant_index(reply_table)
        self._cache: dict[str, ReplyTableEntry | None] = {}

    def match_comment(self, comment: str) -> MatchResult:
        normalized_comment = normalize(comment)
        if normalized_comment in self._variant_index:
            return MatchResult(entry=self._variant_index[normalized_comment], normalized_comment=normalized_comment)
        if normalized_comment not in self._cache:
            reply_id = self._decisions_client.decide(normalized_comment)
            self._cache[normalized_comment] = None if reply_id is None else self._reply_table.by_reply_id(reply_id)
        return MatchResult(entry=self._cache[normalized_comment], normalized_comment=normalized_comment)

    @staticmethod
    def _build_variant_index(reply_table: ReplyTable) -> dict[str, ReplyTableEntry]:
        """One entry per normalized Comment, with any overlap resolved deliberately."""
        index: dict[str, ReplyTableEntry] = {}
        for entry in reply_table.entries:
            for variant in entry.known_variants:
                key = normalize(variant)
                incumbent = index.get(key)
                if incumbent is None or incumbent.reply_id == entry.reply_id:
                    index[key] = entry
                    continue
                index[key] = _resolve_variant_conflict(key, incumbent, entry)
        return index
