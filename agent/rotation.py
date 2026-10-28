"""Phrasing rotation: a durable shuffled deck per Phrasing set.

**This module has no caller, and that is the design rather than an oversight.**
Exactly as in the write path (#7), proving a mechanism and arming it are two
different acts. Rotation is the mechanism; pointing the Comment pass at it is
Graduation (#14), where the Daily cap, Pacing and the Kill switch (#11) make
posting something the agent *may* do. So the deck lives on its own seam and is
exercised directly by tests, and the missing call site keeps the mechanism and
the permission apart.

**Why a deck and not a draw.** A uniform choice over three Phrasings repeats
back to back about one time in three, and clumps -- a pattern, just an irregular
one. A shuffled deck draws without replacement, so no Phrasing repeats
consecutively and every Phrasing appears once per cycle, which is *less*
recognisable than randomness rather than more (ADR 0017). "No pattern to be
recognised" is the goal, and even distribution serves it better than chance.

**What makes two entries one set: a declared map, not programmatic equality.**
``reply-tables/tiktok.json`` is a transcript of the human-readable
``docs/reply-table-tiktok.md`` and carries no ``phrasing_set`` field, and this
ticket does not add one -- a schema invented for a code concern would be a lie
about the record. ADR 0017 records the Account holder's ruling that
``tt-donate-001`` and ``tt-zakat-001`` are *one shared set*: a decision, not an
emergent property of two text blobs that happen to match. So the relation is
declared in code, the way ``VARIANT_PRECEDENCE`` (``agent/matching.py``)
declares which entry owns an overlapping Variant rather than letting file order
decide it. ``PHRASING_SETS`` names the membership, and the deck's construction
**fails loudly** if the table disagrees with it -- if a declared-shared set's
members do not carry equal Phrasings, or if two entries carry equal Phrasings
without being declared together (the silent split that would bring the
duplicate back).

**The deck is durable, per account, and keyed on the set.** Rotation state
survives a restart, like ADR 0009's Daily count: a deck held only in memory
restarts at its first Phrasing and re-posts it (ADR 0017, ``docs/reply-routing.md``
§ Variation). It lives under the account's state root beside ``<account>.sqlite3``
and ``<account>.session-dead.json``, in one file whose decks are keyed on the set
-- never on the entry. A deck keyed on the entry is the bug ADR 0017 names:
``tt-donate-001`` and ``tt-zakat-001`` answering one Post would each draw from
their own deck and could post the identical text twice. The file is written the
way the dead-Session marker already writes it (``O_CREAT|O_TRUNC`` on a temp
file -> ``os.replace`` -> ``chmod 0o600``), because a second atomic-write idiom
in one repo is one too many.

**A one-Phrasing entry is stable; an Escalating entry has nothing to rotate,
and both are structural.** An entry with one approved text has a deck of one,
which always returns that text -- no rotation, as ``docs/reply-routing.md`` puts
it. An ``escalate`` entry holds no text at all and its ``approved_phrasings``
is empty by design (ADR 0014), so its deck is empty and :meth:`PhrasingDeck.draw`
*refuses it loudly* with :class:`NoPhrasingsToRotate`. It never quietly hands
back ``""``: an empty Phrasing posted under the organisation's name would be a
Reply asserting nothing, and the refusal is the seam at which that cannot
happen.

**The deck hands out a :class:`Phrasing`, not a bare string, and that buys a
shape rather than an impossibility.** ADR 0002's "the Router structurally cannot
invent a Reply" has been resting on whoever calls the writer, because
``CommentWriter.write_reply`` takes bare ``str``. A ``Phrasing`` carries the set
it belongs to, the entry it came from, and its text, and ``write_reply`` now
takes one -- so the shape is right and the call site auditable, and a Reviewer
reading a call site can see a Phrasing came from the deck. It does **not** make
invention impossible: a determined caller can still build a ``Phrasing`` by
hand. The type narrows the honest path, and no more is claimed. The deck is not
wired into the writer or the pass (D8).

**What is deliberately not here.** Wiring rotation into the Comment pass or the
write path (#14); the Daily cap, Pacing and the Kill switch (#11); Jev (#8); and
any runtime rewriting, paraphrasing or translation of approved text, which ADR
0017 refuses outright. Phrasings are written and approved in advance; this
module chooses among them and never authors one.
"""

from __future__ import annotations

import json
import os
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from agent.reply_table import ReplyTable, ReplyTableEntry

__all__ = (
    "NoPhrasingsToRotate",
    "Phrasing",
    "PhrasingDeck",
    "PHRASING_SETS",
    "rotation_path",
)


class NoPhrasingsToRotate(RuntimeError):
    """An entry was asked to rotate but holds no approved text.

    This is the ``escalate`` entry's shape (ADR 0014): no text at all, so
    nothing to rotate and nothing the agent is permitted to post. Refused
    loudly rather than resolved to ``""`` -- see the module docstring.
    """


@dataclass(frozen=True)
class Phrasing:
    """One approved text, attributed: the set, the entry, and the words.

    ``set_id`` is the Phrasing set the text rotates within; ``reply_id`` is the
    entry that answered the Comment (so two entries sharing a set still produce
    a Phrasing that names the one actually used); ``text`` is the approved words
    to post.
    """

    set_id: str
    reply_id: str
    text: str


# Which entries point at one shared Phrasing set.
#
# Declared, not derived, following VARIANT_PRECEDENCE (agent/matching.py): a
# relation the code owns is written down, so the order or the text of a data
# file cannot quietly change it. The one pair today is ADR 0017's ruling that
# donating and zakat are one thing here. Entries absent from this map are their
# own set, keyed on their reply_id -- which is every other entry.
#
# `PhrasingDeck` validates this against the loaded table and raises if the table
# disagrees, so editing one of the pair's Phrasings alone fails loudly instead
# of silently unsharing it (ADR 0015: the two entries "neither may be edited
# alone").
PHRASING_SETS: Mapping[str, str] = {
    "tt-donate-001": "donation-zakat",
    "tt-zakat-001": "donation-zakat",
}

_STATE_VERSION = 1


def rotation_path(account: str) -> Path:
    """The account's rotation state under the state convention.

    Beside ``<account>.sqlite3`` and ``<account>.session-dead.json``, because it
    is the same kind of thing: durable per-account state. An explicit ``path``
    lets tests and tools point a deck at a temporary file, exactly as
    ``CommentStore`` does.
    """
    from pw_session import STATE_ROOT

    STATE_ROOT.mkdir(parents=True, exist_ok=True)
    return STATE_ROOT / f"{account}.rotation.json"


class PhrasingDeck:
    """The shuffled decks for one account, drawn one Phrasing at a time.

    Constructed once per account and used across a run. ``draw`` is keyed on the
    entry being answered, resolves that entry's Phrasing set, and advances that
    set's deck -- so two entries that name one set advance one deck (ADR 0017).
    """

    def __init__(
        self,
        reply_table: ReplyTable,
        account: str,
        *,
        path: str | Path | None = None,
        rng: Any | None = None,
        declarations: Mapping[str, str] | None = None,
    ) -> None:
        self._table = reply_table
        self._account = account
        self._path = Path(path) if path is not None else rotation_path(account)
        # Shuffling is the only thing the deck asks of the RNG, and a test can
        # hand it a driven object whose ``shuffle`` is a scripted sequence. The
        # no-consecutive-repeat guarantee is structural (the open-on-last guard
        # below), so it does not depend on the RNG being kind.
        self._rng = rng if rng is not None else random.Random()
        # The declaration defaults to the shipped ``PHRASING_SETS``; a caller may
        # override it, which is how tests drive the deck over a synthetic table
        # without pretending their entries are the shipped ones.
        self._set_by_reply_id, self._phrasings_by_set = _resolve_sets(
            reply_table, declarations
        )
        self._state = _load_state(self._path)

    def draw(self, reply_id: str) -> Phrasing:
        """Advance the entry's set's deck and return one :class:`Phrasing`.

        Refuses an entry with no approved text (an ``escalate`` entry) with
        :class:`NoPhrasingsToRotate`. The draw is durable: the remaining deck
        order and the Phrasing the deck just closed on are written before the
        draw returns.
        """
        entry = self._table.by_reply_id(reply_id)
        set_id = self._set_by_reply_id[entry.reply_id]
        phrasings = self._phrasings_by_set[set_id]
        if not phrasings:
            raise NoPhrasingsToRotate(
                f"{reply_id!r} has no approved Phrasings to rotate"
                f" (status {entry.status!r}); an Escalating entry has nothing to post"
            )

        deck = self._state["decks"].get(set_id)
        if not isinstance(deck, dict):
            # A hand-edited or older file may hold anything under a set key; a
            # non-dict deck is a fresh deck, not a crash.
            deck = {"order": [], "last": None}
            self._state["decks"][set_id] = deck
        # Drop any stored text no longer in the set (the table was edited), and
        # any duplicate, so the deck only ever deals currently-approved words in
        # the order it holds.
        allowed = set(phrasings)
        stored_order = deck.get("order")
        if not isinstance(stored_order, list):
            stored_order = []
        order = _distinct([text for text in stored_order if text in allowed])
        last = deck.get("last") if isinstance(deck.get("last"), str) else None
        if not order:
            order = list(phrasings)
            self._rng.shuffle(order)
            order = _open_off_last(order, last)

        text = order.pop(0)
        deck["order"] = order
        deck["last"] = text
        _write_state(self._path, self._state)
        return Phrasing(set_id=set_id, reply_id=entry.reply_id, text=text)


def _resolve_sets(
    reply_table: ReplyTable,
    declarations: Mapping[str, str] | None = None,
) -> tuple[dict[str, str], dict[str, tuple[str, ...]]]:
    """Map every entry to its set, and every set to its Phrasings.

    Validates the declared ``PHRASING_SETS`` against the loaded table and raises
    ``ValueError`` where they disagree. The checks are deliberately both ways:
    a declaration the table does not honour, and a table equality the
    declaration does not honour, are the two ways the shared-set guarantee can
    break silently.
    """
    if declarations is None:
        declarations = PHRASING_SETS
    by_reply_id = {entry.reply_id: entry for entry in reply_table.entries}

    for reply_id in declarations:
        if reply_id not in by_reply_id:
            raise ValueError(
                f"PHRASING_SETS names {reply_id!r}, which is not in the reply "
                "table. Remove it, or fix the reply id; do not leave a "
                "declaration pointing at nothing."
            )

    set_by_reply_id = {
        entry.reply_id: declarations.get(entry.reply_id, entry.reply_id)
        for entry in reply_table.entries
    }

    # A declared set's members must actually carry the same Phrasings; otherwise
    # there is no one deck to draw from, and editing one of the pair alone
    # (ADR 0015 forbids it) must fail here rather than split the set silently.
    groups: dict[str, list[ReplyTableEntry]] = {}
    for entry in reply_table.entries:
        groups.setdefault(set_by_reply_id[entry.reply_id], []).append(entry)
    phrasings_by_set: dict[str, tuple[str, ...]] = {}
    for set_id, members in groups.items():
        first = members[0]
        for member in members[1:]:
            if member.approved_phrasings != first.approved_phrasings:
                raise ValueError(
                    f"PHRASING_SETS declares {sorted(m.reply_id for m in members)} "
                    f"as one set {set_id!r}, but {first.reply_id!r} and "
                    f"{member.reply_id!r} do not carry the same Phrasings "
                    "(ADR 0015: the pair may not be edited alone)."
                )
        phrasings_by_set[set_id] = tuple(first.approved_phrasings)

    # The other direction: two entries that DO carry equal, non-empty Phrasings
    # must be declared together. Left undeclared they would each keep a private
    # deck and could post the same text twice on one Post -- the duplicate the
    # shared set exists to remove -- with nothing failing to say so.
    for index, first in enumerate(reply_table.entries):
        if not first.approved_phrasings:
            continue
        for second in reply_table.entries[index + 1 :]:
            if second.approved_phrasings != first.approved_phrasings:
                continue
            if set_by_reply_id[first.reply_id] == set_by_reply_id[second.reply_id]:
                continue
            raise ValueError(
                f"{first.reply_id!r} and {second.reply_id!r} carry equal Phrasings "
                "but are declared as different sets, so one Post could receive the "
                "same text twice. Declare them one set in PHRASING_SETS; do not let "
                "two identical decks answer one Post."
            )

    for set_id, phrasings in phrasings_by_set.items():
        if len(set(phrasings)) != len(phrasings):
            raise ValueError(
                f"set {set_id!r} repeats one Phrasing text, so a consecutive "
                "repeat cannot be avoided; every Phrasing of a set must be distinct."
            )
        members = [e.reply_id for e in groups[set_id]]
        if len(members) > 1 and len(phrasings) < 2:
            # ADR 0017: "a shared deck of one still posts the same words twice."
            # A shared set that cannot rotate is the bug it was meant to fix.
            raise ValueError(
                f"set {set_id!r} is shared by {sorted(members)} but holds fewer "
                "than two Phrasings, so the second entry would still post the "
                "same text (ADR 0017); a shared set needs at least two Phrasings."
            )

    return set_by_reply_id, phrasings_by_set


def _distinct(texts: list[str]) -> list[str]:
    """The texts in order, with later duplicates dropped."""
    seen: set[str] = set()
    out: list[str] = []
    for text in texts:
        if text not in seen:
            seen.add(text)
            out.append(text)
    return out


def _open_off_last(order: list[str], last: str | None) -> list[str]:
    """Make a freshly shuffled deck not open on the Phrasing that just closed.

    ADR 0017: "reshuffle, and re-draw if the reshuffle would open on the
    Phrasing that just closed." Swapping the offending first Phrasing with the
    first *different* one is that re-draw made deterministic: it cannot loop
    forever, and with two or more distinct Phrasings it always succeeds. The
    set's distinctness is validated upstream, so a genuinely unavoidable repeat
    never reaches here.
    """
    if last is None or len(order) < 2 or order[0] != last:
        return order
    for index in range(1, len(order)):
        if order[index] != last:
            order[0], order[index] = order[index], order[0]
            break
    return order


def _load_state(path: Path) -> dict[str, Any]:
    """Read the durable decks, treating anything unreadable as a fresh start.

    A missing file is the first run. A corrupt one loses rotation *history* but
    never posts unapproved text -- the worst case is a repeat, which is a
    cosmetic cost, not a safety one -- so it is not worth refusing a run over.
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"version": _STATE_VERSION, "decks": {}}
    if not isinstance(data, dict) or data.get("version") != _STATE_VERSION:
        return {"version": _STATE_VERSION, "decks": {}}
    if not isinstance(data.get("decks"), dict):
        return {"version": _STATE_VERSION, "decks": {}}
    return {"version": _STATE_VERSION, "decks": data["decks"]}


def _write_state(path: Path, state: dict[str, Any]) -> None:
    """Write the decks atomically, the way the dead-Session marker writes.

    ``O_CREAT|O_TRUNC`` on a temp file, ``os.replace`` to publish, ``0o600`` so
    a half-written file is never the one on disk.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.chmod(temporary, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            descriptor = -1
            json.dump(state, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    os.replace(temporary, path)
    os.chmod(path, 0o600)
