"""Phrasing rotation: a durable shuffled deck per Phrasing set (ticket 10).

Each test maps to an acceptance criterion, and every guarantee is pinned by a
test that would fail if the mechanism were a uniform ``random.choice``. The RNG
is not trusted to be kind: where a specific sequence matters the deck is handed
a *driven* shuffle (``DrivenShuffle``) whose scripted order is the whole point,
and the no-consecutive-repeat and even-distribution tests are run over many
seeds so no single lucky seed can carry them.

No Session, no network: the deck touches one JSON file under a temp directory,
as the Comment record touches one sqlite file.
"""

from __future__ import annotations

import json
import random
import re
import stat
from pathlib import Path

import pytest

from agent import rotation
from agent.reply_table import ReplyTable, ReplyTableEntry, load_reply_table
from agent.rotation import (
    NoPhrasingsToRotate,
    PHRASING_SETS,
    Phrasing,
    PhrasingDeck,
    _resolve_sets,
    rotation_path,
)


class DrivenShuffle:
    """An RNG stand-in whose only job is to deal a scripted deck order.

    The deck calls ``shuffle`` exactly when it reshuffles, so this is how a test
    makes a reshuffle open on a known Phrasing -- the case ADR 0017's
    "re-draw if the reshuffle would open on the Phrasing that just closed" is
    about. If the deck stopped asking, ``calls`` would stay 0 and the test that
    asserts on it would fail.
    """

    def __init__(self, orders: list[list[str]]) -> None:
        self.orders = list(orders)
        self.calls = 0

    def shuffle(self, seq: list[str]) -> None:
        assert self.calls < len(self.orders), "the deck reshuffled more than scripted"
        seq[:] = self.orders[self.calls]
        self.calls += 1


def _entry(
    reply_id: str,
    phrasings: tuple[str, ...],
    *,
    status: str = "approved",
    intent: str = "GREETING",
) -> ReplyTableEntry:
    return ReplyTableEntry(
        reply_id=reply_id,
        language="ms",
        intent=intent,
        status=status,
        approved_phrasings=phrasings,
        matching_criteria="invented criteria",
        known_variants=(),
        minimum_match_threshold=0.65,
    )


def _deck(
    tmp_path: Path,
    *,
    account: str = "acct",
    rng=None,
    table=None,
    name="acct",
    declarations=None,
):
    return PhrasingDeck(
        table or load_reply_table(),
        account,
        path=tmp_path / f"{name}.rotation.json",
        rng=rng,
        declarations=declarations,
    )


# --- D2: the set is declared in code, and the table must agree ---------------- #


def test_the_shipped_table_declares_donation_and_zakat_as_one_shared_set() -> None:
    # ADR 0017's ruling, made structural: the two entries point at one set, and
    # they hold the same text so there is one deck to draw from. They are equal
    # *today* -- but equality is evidence the declaration is honoured, not the
    # rule that creates the set.
    assert PHRASING_SETS["tt-donate-001"] == PHRASING_SETS["tt-zakat-001"]
    table = load_reply_table()
    donate = table.by_reply_id("tt-donate-001")
    zakat = table.by_reply_id("tt-zakat-001")
    assert donate.approved_phrasings == zakat.approved_phrasings
    assert len(donate.approved_phrasings) >= 2

    sets, phrasings = _resolve_sets(table)
    assert sets["tt-donate-001"] == sets["tt-zakat-001"] == "donation-zakat"
    assert phrasings["donation-zakat"] == donate.approved_phrasings


def test_a_declared_shared_set_whose_members_differ_fails_loudly(monkeypatch) -> None:
    # Someone edited one of the pair alone. ADR 0015 says the two "neither may be
    # edited alone", and a shared deck cannot be built from two different lists,
    # so this must fail rather than silently split the set.
    monkeypatch.setattr(rotation, "PHRASING_SETS", {"tt-a": "shared", "tt-b": "shared"})
    table = ReplyTable(
        entries=(
            _entry("tt-a", ("one", "two")),
            _entry("tt-b", ("one", "two", "three")),
        )
    )
    with pytest.raises(ValueError, match="edited alone"):
        _resolve_sets(table)


def test_two_entries_with_equal_phrasings_must_be_declared_together(monkeypatch) -> None:
    # The silent-split bug: two entries hold identical text but the code declares
    # them separate, so each keeps a private deck and one Post can receive the
    # same reply twice. Nothing about the text alone would fail; the declaration
    # has to, which is why equality is checked against it.
    monkeypatch.setattr(rotation, "PHRASING_SETS", {})
    table = ReplyTable(
        entries=(_entry("tt-a", ("one", "two")), _entry("tt-b", ("one", "two")))
    )
    with pytest.raises(ValueError, match="same text twice"):
        _resolve_sets(table)


def test_a_declaration_naming_an_entry_not_in_the_table_fails_loudly(monkeypatch) -> None:
    monkeypatch.setattr(rotation, "PHRASING_SETS", {"tt-ghost": "ghost-set"})
    with pytest.raises(ValueError, match="not in the reply table"):
        _resolve_sets(ReplyTable(entries=(_entry("tt-a", ("one", "two")),)))


def test_a_shared_set_of_fewer_than_two_phrasings_fails_loudly(monkeypatch) -> None:
    # ADR 0017: "a shared deck of one still posts the same words twice." A shared
    # set that cannot rotate is the bug the shared set exists to fix.
    monkeypatch.setattr(rotation, "PHRASING_SETS", {"tt-a": "shared", "tt-b": "shared"})
    table = ReplyTable(
        entries=(_entry("tt-a", ("only",)), _entry("tt-b", ("only",)))
    )
    with pytest.raises(ValueError, match="at least two Phrasings"):
        _resolve_sets(table)


def test_a_repeated_phrasing_within_a_set_fails_loudly(monkeypatch) -> None:
    # A set with a duplicate text cannot avoid a consecutive repeat when that
    # text comes up twice; refuse it rather than deal the same words back to back.
    monkeypatch.setattr(rotation, "PHRASING_SETS", {})
    with pytest.raises(ValueError, match="distinct"):
        _resolve_sets(ReplyTable(entries=(_entry("tt-a", ("same", "same")),)))


# --- AC 1: a shuffled deck never repeats consecutively, reshuffle included ---- #


def test_no_phrasing_repeats_consecutively_across_many_seeds(tmp_path) -> None:
    # A uniform draw would repeat back to back about one time in three, so over
    # 300 draws any seed would fail this. Twenty seeds means no single lucky one
    # can carry the guarantee.
    phrasings = load_reply_table().by_reply_id("tt-donate-001").approved_phrasings
    for seed in range(20):
        deck = _deck(tmp_path, rng=random.Random(seed), name=f"acct-{seed}")
        texts = [deck.draw("tt-donate-001").text for _ in range(300)]
        assert all(a != b for a, b in zip(texts, texts[1:])), f"seed {seed} repeated"
        assert set(texts) == set(phrasings)


def test_a_reshuffle_does_not_open_on_the_phrasing_that_just_closed(tmp_path) -> None:
    # Driven so the *second* shuffle deliberately opens on the Phrasing that just
    # closed. The deck must re-draw off it; a mechanism that trusted the shuffle
    # would return P1 back to back here and this test would catch it.
    phrase = load_reply_table().by_reply_id("tt-donate-001").approved_phrasings
    p1, p2, p3 = phrase
    rng = DrivenShuffle([[p1, p2, p3], [p3, p1, p2]])
    deck = _deck(tmp_path, rng=rng)

    assert [deck.draw("tt-donate-001").text for _ in range(3)] == [p1, p2, p3]
    fourth = deck.draw("tt-donate-001")
    assert fourth.text != p3, "the reshuffle opened on the Phrasing that just closed"
    # It re-drew off the closing Phrasing and kept the deck a whole permutation.
    assert {fourth.text, deck.draw("tt-donate-001").text, deck.draw("tt-donate-001").text} == set(
        phrase
    )


# --- AC 2: even distribution, not a clump ------------------------------------- #


def test_a_full_cycle_deals_every_phrasing_exactly_once(tmp_path) -> None:
    phrasings = load_reply_table().by_reply_id("tt-doa-001").approved_phrasings
    for seed in range(20):
        deck = _deck(tmp_path, rng=random.Random(seed), name=f"acct-{seed}")
        cycle = [deck.draw("tt-doa-001").text for _ in range(len(phrasings))]
        assert sorted(cycle) == sorted(phrasings), f"seed {seed} clumped: {cycle}"


def test_every_phrasing_appears_equally_over_a_section(tmp_path) -> None:
    # Nine draws over a three-Phrasing set is three full cycles, so each text
    # appears exactly three times. random.choice would clump on most seeds.
    phrasings = load_reply_table().by_reply_id("tt-praise-001").approved_phrasings
    for seed in range(20):
        deck = _deck(tmp_path, rng=random.Random(seed), name=f"acct-{seed}")
        texts = [deck.draw("tt-praise-001").text for _ in range(3 * len(phrasings))]
        counts = {text: texts.count(text) for text in phrasings}
        assert counts == {text: 3 for text in phrasings}, f"seed {seed}: {counts}"


# --- AC 3: one Phrasing is stable; an Escalation has nothing ------------------ #


def test_an_entry_with_one_phrasing_is_stable(tmp_path) -> None:
    table = ReplyTable(entries=(_entry("tt-one", ("only text",)),))
    deck = _deck(tmp_path, table=table, declarations={})
    assert [deck.draw("tt-one").text for _ in range(5)] == ["only text"] * 5


def test_an_escalating_entry_has_nothing_to_rotate_and_is_refused(tmp_path) -> None:
    # D5, structural: tt-join-001 holds no text by design (ADR 0014), so its deck
    # is empty. It must refuse loudly and never hand back "".
    table = load_reply_table()
    assert table.by_reply_id("tt-join-001").approved_phrasings == ()
    deck = _deck(tmp_path)
    with pytest.raises(NoPhrasingsToRotate):
        deck.draw("tt-join-001")
    # The refusal happens before any state is written, so an Escalation leaves no
    # half-built deck behind.
    assert not (tmp_path / "acct.rotation.json").exists()


def test_an_escalating_entry_declared_as_a_set_still_refuses(monkeypatch, tmp_path) -> None:
    # The refusal is about holding no text, not about being a singleton: an
    # escalate entry never yields a Phrasing whatever set it is filed under.
    table = ReplyTable(
        entries=(_entry("tt-join", (), status="escalate", intent="JOIN_ENQUIRY"),)
    )
    deck = _deck(tmp_path, table=table, declarations={})
    with pytest.raises(NoPhrasingsToRotate, match="tt-join"):
        deck.draw("tt-join")


# --- AC 4: two entries on one set share one deck ------------------------------ #


def test_two_entries_naming_one_set_share_one_rotation(tmp_path) -> None:
    # The donation and zakat entries must draw from the *same* deck: a Post
    # carrying one donation question and one zakat question gets different
    # courtesy lines, never the same text twice (ADR 0017).
    deck = _deck(tmp_path, rng=random.Random(7))
    donation = deck.draw("tt-donate-001")
    zakat = deck.draw("tt-zakat-001")
    assert donation.set_id == zakat.set_id == "donation-zakat"
    assert donation.text != zakat.text
    # Each Phrasing names the entry it actually answered, not merely its set.
    assert donation.reply_id == "tt-donate-001"
    assert zakat.reply_id == "tt-zakat-001"


def test_two_entries_on_one_set_never_post_the_same_text_twice_on_one_post(tmp_path) -> None:
    # A Post that asks both questions contributes two draws. Interleave many such
    # Posts and the shared deck still never hands the same text to both.
    deck = _deck(tmp_path, rng=random.Random(11))
    for _ in range(50):
        first = deck.draw("tt-donate-001")
        second = deck.draw("tt-zakat-001")
        assert first.text != second.text


# --- AC 5: the deck is durable and does not restart at its first Phrasing ----- #


def test_rotation_survives_a_restart_and_continues_the_deck(tmp_path) -> None:
    # The driven shuffle is the point: a restart that reseeded from scratch would
    # shuffle again (calls == 1) and deal the first Phrasing a second time. The
    # correct deck reads the persisted remaining order, does not shuffle, and
    # deals the one Phrasing left in the cycle.
    phrase = load_reply_table().by_reply_id("tt-donate-001").approved_phrasings
    p1, p2, p3 = phrase
    first_run = _deck(tmp_path, rng=DrivenShuffle([[p1, p2, p3]]))
    assert first_run.draw("tt-donate-001").text == p1
    assert first_run.draw("tt-donate-001").text == p2

    after_restart = DrivenShuffle([[p1, p2, p3]])
    second_run = _deck(tmp_path, rng=after_restart)
    third = second_run.draw("tt-donate-001")
    assert third.text == p3, "the deck restarted at its first Phrasing"
    assert after_restart.calls == 0, "the deck reshuffled instead of continuing"


def test_rotation_state_is_per_account(tmp_path) -> None:
    # Two accounts are two decks on disk: one account's draws must not advance
    # the other's rotation.
    table = ReplyTable(entries=(_entry("tt-one", ("only",)),))
    a = _deck(tmp_path, account="a", table=table, name="a", declarations={})
    b = _deck(tmp_path, account="b", table=table, name="b", declarations={})
    a.draw("tt-one")
    assert (tmp_path / "a.rotation.json").exists()
    assert not (tmp_path / "b.rotation.json").exists()
    b.draw("tt-one")
    assert (tmp_path / "b.rotation.json").exists()


def test_the_state_file_is_not_world_readable(tmp_path) -> None:
    deck = _deck(tmp_path)
    deck.draw("tt-greet-001")
    path = tmp_path / "acct.rotation.json"
    assert stat.S_IMODE(path.stat().st_mode) & 0o077 == 0


def test_rotation_path_follows_the_account_state_convention() -> None:
    from pw_session import STATE_ROOT

    assert rotation_path("acct") == STATE_ROOT / "acct.rotation.json"
    assert (
        rotation_path("acct")
        == Path.home() / ".config" / "social-bot" / "state" / "acct.rotation.json"
    )


def test_the_state_file_records_the_remaining_deck_and_the_last_phrasing(tmp_path) -> None:
    # The durable shape: the order still to be dealt, and the Phrasing just
    # closed, so a reshuffle after a restart can still avoid reopening on it.
    phrase = load_reply_table().by_reply_id("tt-donate-001").approved_phrasings
    deck = _deck(tmp_path, rng=DrivenShuffle([list(phrase)]))
    deck.draw("tt-donate-001")
    state = json.loads((tmp_path / "acct.rotation.json").read_text())
    stored = state["decks"]["donation-zakat"]
    assert stored["last"] == phrase[0]
    assert stored["order"] == list(phrase[1:])


def test_a_corrupt_state_file_is_a_fresh_start_not_a_crash(tmp_path) -> None:
    (tmp_path / "acct.rotation.json").write_text("{ not json")
    deck = _deck(tmp_path)
    assert deck.draw("tt-greet-001").text


# --- D7: the deck hands out a Phrasing, not a bare string --------------------- #


def test_the_deck_hands_out_a_phrasing_naming_its_set_entry_and_text(tmp_path) -> None:
    deck = _deck(tmp_path)
    phrasing = deck.draw("tt-zakat-001")
    assert isinstance(phrasing, Phrasing)
    assert phrasing.set_id == "donation-zakat"
    assert phrasing.reply_id == "tt-zakat-001"
    assert phrasing.text in load_reply_table().by_reply_id("tt-zakat-001").approved_phrasings


# --- AC 6: every Phrasing asserts the same facts as the canonical text -------- #


def _numeric_runs(text: str) -> list[str]:
    return re.findall(r"\d+", text)


def test_every_phrasing_carries_the_canonical_texts_numbers_identically() -> None:
    # The money-safety check (ADR 0017): a paraphrased account number is money to
    # a stranger. Every numeric run of the canonical text must appear in each
    # Phrasing, in the same order and spelling.
    for entry in load_reply_table().entries:
        if not entry.approved_phrasings:
            continue
        canonical_runs = _numeric_runs(entry.approved_phrasings[0])
        for index, phrasing in enumerate(entry.approved_phrasings, 1):
            assert _numeric_runs(phrasing) == canonical_runs, (
                f"{entry.reply_id} Phrasing {index} changes the numbers: "
                f"{_numeric_runs(phrasing)} != {canonical_runs}"
            )


def test_no_phrasing_introduces_a_number_the_canonical_text_lacks() -> None:
    # The other direction, stated on its own because it is the failure mode: a
    # Phrasing that adds "a second account for zakat" would pass the subset test
    # above and fail here.
    for entry in load_reply_table().entries:
        if not entry.approved_phrasings:
            continue
        canonical_runs = set(_numeric_runs(entry.approved_phrasings[0]))
        for index, phrasing in enumerate(entry.approved_phrasings, 1):
            introduced = set(_numeric_runs(phrasing)) - canonical_runs
            assert not introduced, (
                f"{entry.reply_id} Phrasing {index} introduces numbers the "
                f"canonical text does not have: {sorted(introduced)}"
            )


def test_the_canonical_block_appears_verbatim_in_every_donation_and_zakat_phrasing() -> None:
    # The bank, the number and the payee are the Account holder's verbatim words
    # and must survive every Phrasing unchanged. Only the courtesy line above the
    # block may vary.
    table = load_reply_table()
    for reply_id in ("tt-donate-001", "tt-zakat-001"):
        entry = table.by_reply_id(reply_id)
        canonical = entry.approved_phrasings[0]
        assert "\n\n" in canonical, "the canonical text no longer contains a block"
        block = canonical.split("\n\n", 1)[1]
        assert block.strip(), f"{reply_id}: the canonical block is empty"
        for index, phrasing in enumerate(entry.approved_phrasings, 1):
            assert block in phrasing, (
                f"{reply_id} Phrasing {index} does not carry the canonical block "
                f"verbatim:\n{phrasing!r}"
            )
