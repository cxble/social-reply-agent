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
        index: dict[str, ReplyTableEntry] = {}
        for entry in reply_table.entries:
            for variant in entry.known_variants:
                index[normalize(variant)] = entry
        return index
