from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from agent.matching import Matcher
from agent.normalize import CORE, normalize
from agent.reply_table import STATUSES, load_reply_table, reply_table_path


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
    for intent in {'DOA_BLESSING', 'GREETING', 'PRAISE_ENCOURAGE', 'BENEFICIARY_THANKS', 'CONVERT_CONGRATS'}:
        assert by_intent[intent] == 0.65
    assert by_intent['JOIN_ENQUIRY'] == 0.2


def test_doa_request_threshold_is_carried_but_not_settled_here() -> None:
    """`DOA_REQUEST` sits in no tier the document names, and this test must not invent one.

    ADR 0019 lists a Consequential tier, an Acknowledgement tier, an Escalation gate
    band and a Floor. `DOA_REQUEST` is in none of them: it is the entry the document
    leaves open, and the architecture ticket decides where it lands. The table carries
    a working value so the matching path is exercised end to end -- that value is not
    an architectural rule, and asserting it as one here would settle the dispute by
    accident. The assertion below is agreement with the reviewed record, which labels
    the number provisional, not agreement with a tier.
    """
    table = load_reply_table()
    by_intent = {entry.intent: entry for entry in table.entries}
    assert 'DOA_REQUEST' in by_intent
    recorded = json.loads(
        (Path(__file__).parent / "fixtures" / "approval_record_tiktok.json").read_text()
    )
    recorded_entry = next(e for e in recorded["entries"] if e["intent"] == "DOA_REQUEST")
    assert recorded_entry["threshold_status"] == "provisional", (
        "the record no longer marks the DOA_REQUEST threshold provisional; if the "
        "architecture ticket has settled it, fix this test deliberately and cite the ADR"
    )
    assert by_intent['DOA_REQUEST'].minimum_match_threshold == recorded_entry["minimum_match_threshold"]
    assert by_intent['DOA_REQUEST'].status == "provisional"


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
