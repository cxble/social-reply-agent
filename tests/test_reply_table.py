from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

import pytest

from agent.matching import VARIANT_PRECEDENCE, Matcher
from agent.normalize import CORE, normalize
from agent.reply_table import STATUSES, ReplyTable, ReplyTableEntry, load_reply_table, reply_table_path

DOCUMENT_LINES = (
    Path(__file__).resolve().parent.parent / "docs" / "reply-table-tiktok.md"
).read_text(encoding="utf-8").splitlines()

RECORD_PATH = Path(__file__).parent / "fixtures" / "approval_record_tiktok.json"

ADR_LINES = (
    Path(__file__).resolve().parent.parent
    / "docs"
    / "adr"
    / "0019-an-uncertain-reading-never-reaches-the-write-path.md"
).read_text(encoding="utf-8").splitlines()


def _adr_tier(tier: str) -> set[str]:
    """The Intents the ADR's tier table names in one of its tiers."""
    row = next(line for line in ADR_LINES if line.startswith(f"| **{tier}** |"))
    cells = [cell.strip() for cell in row.strip().strip("|").split("|")]
    return set(re.findall(r"`([A-Z_]+)`", cells[1]))

# The two Comments the approval record files under both `DOA_BLESSING` and
# `PRAISE_ENCOURAGE`, in the record's own spellings.
OVERLAPPING_COMMENTS = (
    "good job. semuga dipermudahkan segala urusan Perubatan Dan kembali sihat",
    "terbaik bro Ben. Keep it up till it last breath. Amieen Ya Alloh.",
)


def _document_line(number: int) -> str:
    return DOCUMENT_LINES[number - 1]


@dataclass
class DecisionsClientDouble:
    reply_id: str | None = None
    call_count: int = 0
    seen: list[str] | None = None
    raises: bool = False

    def __post_init__(self) -> None:
        if self.seen is None:
            self.seen = []

    def decide(self, normalized_comment: str) -> str | None:
        self.call_count += 1
        self.seen.append(normalized_comment)
        if self.raises:
            raise AssertionError('Router should not be called')
        return self.reply_id


def test_table_loads_from_version_control_with_all_fields() -> None:
    table = load_reply_table()
    assert reply_table_path().is_file()
    assert len(table.entries) == 10
    for entry in table.entries:
        assert entry.reply_id
        assert entry.language
        assert entry.intent
        assert entry.status in STATUSES
        assert isinstance(entry.approved_phrasings, tuple)
        assert isinstance(entry.matching_criteria, str)
        assert isinstance(entry.known_variants, tuple)
        assert isinstance(entry.minimum_match_threshold, float)


def test_thresholds_respect_the_floor_where_the_entry_can_post() -> None:
    """The 0.50 Floor governs posting, so it binds exactly the entries that can post.

    An escalation-only entry never posts; it sits at an Escalation gate to route the
    Comment to a human. Holding it to the posting Floor would be a category error, and
    is the reason this test is written over `status` rather than over every entry.
    """
    table = load_reply_table()
    for entry in table.entries:
        if entry.status == "escalate":
            assert entry.minimum_match_threshold == 0.20, entry.reply_id
            assert entry.approved_phrasings == ()
        else:
            assert entry.minimum_match_threshold >= 0.50, entry.reply_id


def test_settled_tier_values_are_as_the_document_assigns_them() -> None:
    table = load_reply_table()
    by_intent = {entry.intent: entry.minimum_match_threshold for entry in table.entries}
    for intent in {'DONATION_ENQUIRY', 'ZAKAT_SEDEKAH_ENQUIRY'}:
        assert by_intent[intent] == 0.9
    for intent in {'DOA_BLESSING', 'DOA_REQUEST', 'GREETING', 'PRAISE_ENCOURAGE', 'BENEFICIARY_THANKS', 'CONVERT_CONGRATS'}:
        assert by_intent[intent] == 0.65
    assert by_intent['JOIN_ENQUIRY'] == 0.2


def test_the_adr_names_exactly_the_entries_its_tiers_bind() -> None:
    """The tier numbers are a claim about the ADR, so the ADR has to agree with them.

    This is the drift that produced the `DOA_REQUEST` item: the ADR's Acknowledgement
    row simply omitted the entry, so 0.65 had no architectural basis in the one place
    the tiers are justified. `HELP_REQUEST` is absent from the table by design -- it is
    an Escalation gate with no entry to hold a threshold -- so the gates are compared
    against the ADR only for the Intents the table actually carries.
    """
    table = load_reply_table()
    for tier, threshold in (("Acknowledgement", 0.65), ("Consequential", 0.9)):
        carried = {
            entry.intent for entry in table.entries if entry.minimum_match_threshold == threshold
        }
        assert _adr_tier(tier) == carried, (
            f"{tier}: the ADR names {sorted(_adr_tier(tier))} and the table binds "
            f"{sorted(carried)} at {threshold}"
        )
    gates = _adr_tier("Escalation gates")
    assert gates == {"HELP_REQUEST", "JOIN_ENQUIRY"}
    carried_gates = {
        entry.intent for entry in table.entries if entry.minimum_match_threshold == 0.2
    }
    assert carried_gates <= gates, 'an entry sits at the help threshold that the ADR does not name'


def test_doa_request_is_an_acknowledgement_and_its_number_is_uncalibrated() -> None:
    """`DOA_REQUEST` is in the Acknowledgement tier; the *number* is not yet calibrated.

    The document sets the tiers by what a wrong Reply costs and gives the
    acknowledgement classes 0.65, which is where this entry belongs: its rows post a
    canned acknowledgement that "promises no action beyond the doa itself". What is
    not settled is the calibration -- the document says once, for the whole table,
    that the numbers are provisional because they are claims about a Router that does
    not exist in this repository. The tier and the uncertainty are recorded in
    different places on purpose: the tier binds the entry, the uncertainty covers all
    ten numbers at once, and repeating it per entry would restate a single sentence
    ten times.
    """
    table = load_reply_table()
    entry = next(e for e in table.entries if e.intent == 'DOA_REQUEST')
    assert entry.minimum_match_threshold == 0.65, 'the acknowledgement tier is 0.65'
    assert entry.status == 'approved'

    record = json.loads(RECORD_PATH.read_text())
    assert record['threshold_status'] == 'provisional'
    assert record['threshold_status_doc_lines'] == [961]
    assert 'provisional' in _document_line(961), (
        'the record cites a line that no longer says the numbers are provisional'
    )
    for recorded in record['entries']:
        assert 'threshold_status' not in recorded, (
            f"{recorded['reply_id']}: calibration is recorded per entry as well as for "
            "the table as a whole; the document states it once"
        )
    assert 'threshold_status' not in json.loads(reply_table_path().read_text())[0]


def test_escalation_gated_intents_hold_no_postable_text() -> None:
    table = load_reply_table()
    join = table.by_reply_id('tt-join-001')
    assert join.intent == 'JOIN_ENQUIRY'
    assert join.status == 'escalate'
    assert join.approved_phrasings == ()


def test_known_variant_matches_without_model_call() -> None:
    table = load_reply_table()
    client = DecisionsClientDouble(raises=True)
    matcher = Matcher(table, client)
    result = matcher.match_comment('Saya nak join bleh x')
    assert result.entry is not None
    assert result.entry.reply_id == 'tt-join-001'
    assert client.call_count == 0


def test_identical_comment_hits_router_once_ever() -> None:
    table = load_reply_table()
    client = DecisionsClientDouble(reply_id='tt-praise-001')
    matcher = Matcher(table, client)
    results = [matcher.match_comment('bagusss') for _ in range(3)]
    assert client.call_count == 1
    assert [result.entry.reply_id if result.entry else None for result in results] == ['tt-praise-001'] * 3
    assert results[0].normalized_comment == results[1].normalized_comment == results[2].normalized_comment


def test_no_bare_formula_appears_in_known_variants() -> None:
    table = load_reply_table()
    formula_words = CORE
    for entry in table.entries:
        for variant in entry.known_variants:
            normalized = normalize(variant)
            assert normalized not in formula_words
            assert not all(word in formula_words for word in normalized.split())


def test_join_is_the_only_entry_present_with_no_text() -> None:
    table = load_reply_table()
    empty = {entry.intent for entry in table.entries if not entry.approved_phrasings}
    assert empty == {'JOIN_ENQUIRY'}


def test_help_request_has_no_entry_at_all() -> None:
    """The negative path: `HELP_REQUEST` is a Documented Intent with no reply text.

    `JOIN_ENQUIRY` has an entry that carries no text, so an empty `approved_phrasings`
    is one shape a non-postable Intent can take. `HELP_REQUEST` is the other: there is
    no entry to carry text in the first place, and nothing here may quietly add one.
    """
    table = load_reply_table()
    assert [entry.reply_id for entry in table.entries if entry.intent == 'HELP_REQUEST'] == []


def test_a_help_shaped_comment_is_not_variant_matched() -> None:
    """It reaches the Router instead, which is what routes it to a human.

    A help-shaped Comment must not be answered by a `known_variant` hit: a variant hit
    returns an entry directly, with no Router call, so an entry that happened to match
    would post a reply to someone asking for help. The Router call below is the point
    of the test -- `call_count == 1` is what proves the Comment was not matched.
    """
    table = load_reply_table()
    client = DecisionsClientDouble(reply_id=None)
    matcher = Matcher(table, client)
    result = matcher.match_comment('macam mana nak mohon bantuan kebajikan untuk keluarga saya')
    assert result.entry is None
    assert client.call_count == 1, 'the Comment was matched by a variant instead of reaching the Router'
    known_forms = {normalize(v) for entry in table.entries for v in entry.known_variants}
    assert result.normalized_comment not in known_forms


def test_a_variant_filed_under_two_intents_resolves_to_the_declared_winner() -> None:
    """A Comment the record files twice is answered by a declared entry, not by file order.

    Both Comments below are in the record under `DOA_BLESSING` *and*
    `PRAISE_ENCOURAGE`, in different spellings that normalize to the same form. The
    blessing entry wins because the praise entry's own `matching_criteria` excludes
    them: praise here is "praise or encouragement with no request and no explicit
    doa", and both Comments carry an explicit doa.
    """
    assert 'tt-doa-002' in VARIANT_PRECEDENCE
    assert 'tt-praise-001' not in VARIANT_PRECEDENCE, (
        'the praise entry must not outrank the blessing entry: its own criteria '
        'exclude a Comment carrying an explicit doa'
    )
    record = json.loads(RECORD_PATH.read_text())
    praise = next(e for e in record['entries'] if e['reply_id'] == 'tt-praise-001')
    assert 'no explicit doa' in praise['matching_criteria']

    table = load_reply_table()
    for comment in OVERLAPPING_COMMENTS:
        client = DecisionsClientDouble(raises=True)
        result = Matcher(table, client).match_comment(comment)
        assert result.entry is not None, comment
        assert result.entry.reply_id == 'tt-doa-002', comment
        assert client.call_count == 0, 'a variant hit must not reach the Router'

    for reply_id in ('tt-doa-002', 'tt-praise-001'):
        carried = {normalize(v) for v in table.by_reply_id(reply_id).known_variants}
        for comment in OVERLAPPING_COMMENTS:
            assert normalize(comment) in carried, (
                f'{reply_id} no longer carries the Comment the record files under it. '
                'The record lists these twice; the overlap is resolved by precedence, '
                'not by deleting a variant from an entry that has one.'
            )


def test_reordering_the_reply_table_cannot_change_which_entry_answers() -> None:
    """Precedence is declared, so the order of the entries in the JSON must not matter."""
    table = load_reply_table()
    shuffled = ReplyTable(entries=tuple(reversed(table.entries)))
    assert [e.reply_id for e in shuffled.entries] != [e.reply_id for e in table.entries]

    for comment in OVERLAPPING_COMMENTS:
        forwards = Matcher(table, DecisionsClientDouble(raises=True)).match_comment(comment)
        backwards = Matcher(shuffled, DecisionsClientDouble(raises=True)).match_comment(comment)
        assert forwards.entry is not None, comment
        assert backwards.entry is not None, comment
        assert forwards.entry.reply_id == backwards.entry.reply_id == 'tt-doa-002', (
            f'{comment!r}: reversing the reply table changed which entry answers it'
        )


def test_an_undeclared_overlap_is_refused_rather_than_resolved_by_order() -> None:
    """A new overlap has to fail loudly, because the alternative is a silent last-writer-wins."""

    def claiming(reply_id: str) -> ReplyTableEntry:
        return ReplyTableEntry(
            reply_id=reply_id,
            language='en',
            intent='PRAISE_ENCOURAGE',
            status='approved',
            approved_phrasings=('invented phrasing',),
            matching_criteria='invented criteria',
            known_variants=('invented shared variant',),
            minimum_match_threshold=0.65,
        )

    overlapping = ReplyTable(
        entries=(claiming('tt-alpha-001'), claiming('tt-beta-001'))
    )
    with pytest.raises(ValueError, match='VARIANT_PRECEDENCE'):
        Matcher(overlapping, DecisionsClientDouble())


def test_doakn_and_doakan_normalize_to_the_same_form_and_hit_tt_doareq_001() -> None:
    """`doakn` is a real observed spelling carried by `tt-doareq-001`, and the
    entry's whole reason for existing is the `tolong doa` misroute. Its two
    spellings must fold to one canonical form so the Comment written `doakn`
    reaches the entry the same way the Comment written `doakan` does.
    """
    assert normalize('tlg doakn sy') == normalize('tolong doakan saya')
    assert normalize('doakn') == normalize('doakan')

    table = load_reply_table()
    client = DecisionsClientDouble(raises=True)
    result = Matcher(table, client).match_comment(
        'tolong doakn saya sahabat untuk saya dn suami dpt pergi buat umrah'
    )
    assert result.entry is not None
    assert result.entry.reply_id == 'tt-doareq-001'
    assert client.call_count == 0, 'a variant hit must not reach the Router'

def test_unseen_comment_written_with_sya_and_tuk_reaches_tt_doareq_001() -> None:
    """`sya` and `tuk` are corpus spellings in `tt-doareq-001`'s own variant, so a
    Comment written with them must reach the entry without a Router call."""
    table = load_reply_table()
    client = DecisionsClientDouble(raises=True)
    result = Matcher(table, client).match_comment(
        'w slm sya teringin nak pergi umrah tapi tak mampu doa kan tuk sya'
    )
    assert result.entry is not None
    assert result.entry.reply_id == 'tt-doareq-001'
    assert client.call_count == 0
    variants = {
        normalize(v)
        for entry in table.entries
        for v in entry.known_variants
        if v != 'w slm sya teringin nak pergi umrah tapi tak mampu doa kan tuk sya'
    }
    spellings = {normalize('w slm saya teringin nak pergi umrah tapi tak mampu doa kan untuk saya')}
    assert result.normalized_comment in spellings, result.normalized_comment
    assert result.normalized_comment not in variants, (
        'the Comment matched a variant, not the new normalizer spellings'
    )


def test_permutations_of_an_undeclared_overlap_agree() -> None:
    """The refusal must not depend on the order the claiming entries appear in."""
    from itertools import permutations

    def claiming(reply_id: str) -> ReplyTableEntry:
        return ReplyTableEntry(
            reply_id=reply_id,
            language='en',
            intent='PRAISE_ENCOURAGE',
            status='approved',
            approved_phrasings=('invented phrasing',),
            matching_criteria='invented criteria',
            known_variants=('invented shared variant',),
            minimum_match_threshold=0.65,
        )

    outcomes = []
    for order in permutations(('tt-alpha-001', 'tt-beta-001', 'tt-gamma-001')):
        table = ReplyTable(entries=tuple(claiming(rid) for rid in order))
        try:
            Matcher(table, DecisionsClientDouble())
            outcomes.append('loaded')
        except ValueError:
            outcomes.append('refused')
    assert len(set(outcomes)) == 1, outcomes


def test_router_unknown_reply_id_is_a_named_failure_and_does_not_poison_the_cache() -> None:
    table = load_reply_table()
    client = DecisionsClientDouble(reply_id='tt-does-not-exist')
    matcher = Matcher(table, client)
    with pytest.raises(KeyError, match='tt-does-not-exist'):
        matcher.match_comment('a comment only the Router decides')
    assert client.call_count == 1

    client.reply_id = 'tt-praise-001'
    result = matcher.match_comment('a comment only the Router decides')
    assert result.entry is not None
    assert result.entry.reply_id == 'tt-praise-001'
    assert client.call_count == 2
