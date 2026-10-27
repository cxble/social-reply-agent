"""Variant matching, the Router seam, and the bars that stand before the write path.

`match_comment` returns a :class:`MatchResult` that carries the **Outcome** the
pass records, so the pass never re-derives the decision a second time in a
different place (D4). Three things decide an Outcome here, in this order:

1. **A declared Variant hit.** A normalized Comment that is one of an entry's
   ``known_variants`` is answered by that entry directly, with no Router call and
   therefore at confidence 1.0 -- above every entry's threshold by construction.
   Which entry answers an overlap is declared in ``VARIANT_PRECEDENCE``, not by
   file order.
2. **The Router's decision.** The Router is handed every entry in the loaded
   table as the options and returns a confidence per option, or ``None`` (nothing
   fits -- the Tail), or ``uncertain=True`` (it declines to choose). It never
   returns text of its own, and a reply id outside the options it was handed is
   refused with :class:`UnknownReplyId` -- the guard against a Router answering
   about something it was not offered.
3. **The two bars over that decision.** An entry is eligible at or above *its
   own* ``minimum_match_threshold`` (Bar 2, per entry, never one global number),
   and two eligible entries of *different* Intents are a conflict (Bar 3). The
   higher of a conflict is never chosen.

## D6 -- what "mutually exclusive" means here, and the direction it errs

`mutually exclusive` is named in `docs/reply-routing.md`, `docs/reply-table-tiktok.md`
and ADR 0019, and **nowhere is there a list of which pairs conflict**. This module
takes the conservative reading, written down because it is a decision rather than a
deduction: **any two eligible entries of different Intents are a conflict.** That
will over-Escalate a genuinely compatible pair such as `GREETING` +
`BENEFICIARY_THANKS`. The direction is chosen deliberately -- posting a wrong Reply
is unrecoverable and public while an extra Escalation costs a human one skim (ADR
0014's asymmetry) -- and narrowing it later is the Account holder's call against the
labelled set. No exclusivity matrix is invented in `reply-tables/tiktok.json`: the
record does not carry one and this ticket does not add schema. Two eligible entries
of the *same* Intent are not a conflict: `tt-doa-001` and `tt-doa-002` are both
`DOA_BLESSING`, so the higher confidence is taken and posted.

## D8 -- what is deliberately not here

The options handed to the Router are every entry in the loaded table; narrowing
them by language is routing step 3 and is not this ticket. The help threshold and
the difficulty signal are a second typed question to the Router that does not
exist yet (ADR 0014 makes `HELP_REQUEST` deliberately not a Reply-table entry), and
they belong to #8. This module owns the policy the seam serves; it does not own the
wire call behind it and never calls a network.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Protocol, Sequence

from agent.normalize import normalize
from agent.record import Outcome
from agent.reply_table import ReplyTable, ReplyTableEntry, UnknownReplyId

__all__ = (
    "UnknownReplyId",
    "Decisions",
    "DecisionsClient",
    "MatchResult",
    "Matcher",
)


class DecisionsClient(Protocol):
    """The Router seam: a decision over the options supplied, never text.

    ``None`` means nothing the Router was offered fits at all -- the Comment is
    a Tail. A decision carrying ``uncertain=True`` means it declined to choose.
    Otherwise it carries a confidence per entry, over the options it was handed.
    """

    def decide(
        self, normalized_comment: str, options: Sequence[ReplyTableEntry]
    ) -> Decisions | None: ...


@dataclass(frozen=True)
class Decisions:
    """The Router's answer about the options it was offered.

    ``confidences`` maps a reply id to the Router's confidence that this entry
    fits the Comment. Ids the Router was not offered are refused by ``Matcher``.
    An entry absent from the mapping is treated as confidence 0.0 -- not eligible
    -- rather than as a claim of fit.
    """

    confidences: Mapping[str, float]
    uncertain: bool = False


@dataclass(frozen=True)
class MatchResult:
    """One Comment's routing decision, carried out whole so the pass records it.

    ``entry`` is the eligible entry that may post or Escalate, or ``None`` when
    the Outcome is one of the non-entry outcomes (a Tail, a bar that refused it,
    an unsure or conflicting reading). ``outcome`` is the decision itself and
    ``detail`` is the human-readable why, both carried so the pass does not
    re-derive them from the entry a second time.
    """

    entry: ReplyTableEntry | None
    normalized_comment: str
    outcome: Outcome
    detail: str = ""


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
    key: str, claimed_by: list[ReplyTableEntry]
) -> ReplyTableEntry:
    """Choose the declared winner among every entry that claims a normalized Comment.

    The refusal is not reduced pairwise: if any two claimants are undeclared, the
    whole key is refused regardless of the order the entries appear in.
    """
    ranked = [entry for entry in claimed_by if entry.reply_id in VARIANT_PRECEDENCE]
    if not ranked:
        raise ValueError(
            f"the variant {key!r} is carried by {', '.join(repr(e.reply_id) for e in claimed_by)}, "
            "and which of them answers it is not declared. Add "
            "the winning entry to VARIANT_PRECEDENCE; do not let the order of the "
            "reply table decide it."
        )
    return min(ranked, key=lambda entry: VARIANT_PRECEDENCE.index(entry.reply_id))


class Matcher:
    def __init__(self, reply_table: ReplyTable, decisions_client: DecisionsClient) -> None:
        self._reply_table = reply_table
        self._decisions_client = decisions_client
        self._variant_index = self._build_variant_index(reply_table)
        self._cache: dict[str, MatchResult] = {}

    def match_comment(self, comment: str) -> MatchResult:
        normalized_comment = normalize(comment)
        if normalized_comment in self._variant_index:
            entry = self._variant_index[normalized_comment]
            return _result_for_entry(entry, normalized_comment)
        if normalized_comment not in self._cache:
            # A refusal (UnknownReplyId) must not poison the cache: the Comment is
            # left undecided and a later call is free to ask again.
            self._cache[normalized_comment] = self._route(normalized_comment)
        return self._cache[normalized_comment]

    def _route(self, normalized_comment: str) -> MatchResult:
        """Turn the Router's decision over the options into an Outcome (Bars 2-3).

        The options are every entry in the loaded table. Narrowing them by
        language is routing step 3 and is not this ticket (D8).
        """
        options = self._reply_table.entries
        decision = self._decisions_client.decide(normalized_comment, options)
        if decision is None:
            return MatchResult(
                entry=None,
                normalized_comment=normalized_comment,
                outcome=Outcome.OUT_OF_SCOPE,
                detail="no Canned reply covers the Comment",
            )
        if decision.uncertain:
            # Bar 3 is not a threshold: an unsure reading has no score to lower,
            # so nothing the decision carries can admit it to a reply.
            return MatchResult(
                entry=None,
                normalized_comment=normalized_comment,
                outcome=Outcome.UNCERTAIN,
                detail="the Router declined to choose",
            )

        options_by_id = {entry.reply_id: entry for entry in options}
        for reply_id in decision.confidences:
            if reply_id not in options_by_id:
                # The Router answered about something it was not offered.
                raise UnknownReplyId(reply_id)

        if not decision.confidences:
            # An answer naming no option at all says what `None` says: nothing the
            # Router was offered fits. It is the Tail. Recording it as a refused
            # bar instead would put a Comment that was never a candidate into the
            # outcome ADR 0019 fixes to `OUT_OF_SCOPE` -- "a reply was warranted
            # and none fits", which the sweep counts as its own class -- so the
            # same state would be measured as two different things.
            return MatchResult(
                entry=None,
                normalized_comment=normalized_comment,
                outcome=Outcome.OUT_OF_SCOPE,
                detail="the Router named no option",
            )

        eligible = [
            (options_by_id[reply_id], confidence)
            for reply_id, confidence in decision.confidences.items()
            if confidence >= options_by_id[reply_id].minimum_match_threshold
        ]
        if not eligible:
            # The Router returned confidences, but every one is under its own
            # entry's threshold -- distinct from `None`, which means nothing fit.
            return MatchResult(
                entry=None,
                normalized_comment=normalized_comment,
                outcome=Outcome.BELOW_MINIMUM_MATCH_THRESHOLD,
                detail=_below_threshold_detail(decision.confidences, options_by_id),
            )

        intents = {entry.intent for entry, _ in eligible}
        if len(intents) > 1:
            # Bar 3, conservative reading (see the module docstring): any two
            # eligible entries of different Intents conflict, and the higher is
            # never chosen. Two of the same Intent take the higher confidence.
            return MatchResult(
                entry=None,
                normalized_comment=normalized_comment,
                outcome=Outcome.CONFLICTING_INTENTS,
                detail="conflicting intents: " + ", ".join(sorted(intents)),
            )

        best_entry = max(eligible, key=lambda item: item[1])[0]
        return _result_for_entry(best_entry, normalized_comment)

    @staticmethod
    def _build_variant_index(reply_table: ReplyTable) -> dict[str, ReplyTableEntry]:
        """One entry per normalized Comment, with any overlap resolved deliberately."""
        index: dict[str, ReplyTableEntry] = {}
        claimants: dict[str, list[ReplyTableEntry]] = {}
        for entry in reply_table.entries:
            for variant in entry.known_variants:
                key = normalize(variant)
                bucket = claimants.setdefault(key, [])
                if entry not in bucket:
                    bucket.append(entry)
        for key, claimed_by in claimants.items():
            if len(claimed_by) == 1:
                index[key] = claimed_by[0]
            else:
                index[key] = _resolve_variant_conflict(key, claimed_by)
        return index


def _result_for_entry(entry: ReplyTableEntry, normalized_comment: str) -> MatchResult:
    """The Outcome an eligible entry produces: post it, or Escalate its gate."""
    if entry.status == "escalate":
        return MatchResult(
            entry=entry,
            normalized_comment=normalized_comment,
            outcome=Outcome.ESCALATION_GATED_INTENT,
            detail=f"{entry.intent} via {entry.reply_id}",
        )
    return MatchResult(
        entry=entry,
        normalized_comment=normalized_comment,
        outcome=Outcome.CANNED_REPLY,
        detail=entry.reply_id,
    )


def _below_threshold_detail(
    confidences: Mapping[str, float], options_by_id: Mapping[str, ReplyTableEntry]
) -> str:
    """Name which bar refused the Comment, for the Dry-run record (ADR 0019)."""
    parts = [
        f"{reply_id} {confidence:.2f}<{options_by_id[reply_id].minimum_match_threshold:.2f}"
        for reply_id, confidence in sorted(confidences.items())
    ]
    return "below minimum_match_threshold: " + ", ".join(parts)
