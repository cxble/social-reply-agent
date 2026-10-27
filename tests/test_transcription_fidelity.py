"""Transcription fidelity: the reply table against the approval record.

`reply-tables/tiktok.json` is what the agent posts from. `docs/reply-table-tiktok.md`
is the Account holder's approval record and is authoritative for every string the
agent may post.

Every other test in this suite runs the *production* table and checks that it behaves
sensibly. That cannot catch a phrase that was invented, reworded, or dropped: a table
full of plausible-looking text the Account holder never approved passes all of them.
The check has to be against the document, by a representation built from the document
and not from the table, which is what `tests/fixtures/approval_record_tiktok.json` is.

It is reviewed, not generated: it carries the verbatim text of each § Sign-off row and
each § Phrasings row, every `known_variants` entry with the document line it was read
from, and an entry for every string the document names but that must *not* be posted,
with the reason. It is compared here in both directions -- no unapproved text in the
table, and no approved text missing from it -- so that neither an addition nor a
deletion passes silently.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from agent.normalize import bare_interjection, normalize
from agent.reply_table import load_reply_table

REPO_ROOT = Path(__file__).resolve().parent.parent
RECORD_PATH = Path(__file__).parent / "fixtures" / "approval_record_tiktok.json"
DOCUMENT_PATH = REPO_ROOT / "docs" / "reply-table-tiktok.md"

DOCUMENT_LINES = DOCUMENT_PATH.read_text(encoding="utf-8").splitlines()

_HEADING = re.compile(r"^###\s+`(tt-[a-z0-9-]+)`")


def _section_of_each_line() -> dict[int, str | None]:
    """The reply-id section each document line falls in, by its nearest heading."""
    section: str | None = None
    sections: dict[int, str | None] = {}
    for number, line in enumerate(DOCUMENT_LINES, 1):
        match = _HEADING.match(line)
        if match:
            section = match.group(1)
        sections[number] = section
    return sections


SECTION_OF_LINE = _section_of_each_line()


@pytest.fixture(scope="module")
def record() -> dict:
    return json.loads(RECORD_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def record_entries(record: dict) -> dict[str, dict]:
    return {entry["reply_id"]: entry for entry in record["entries"]}


@pytest.fixture(scope="module")
def table_entries() -> dict[str, object]:
    return {entry.reply_id: entry for entry in load_reply_table().entries}


def test_the_table_covers_exactly_the_recorded_entries(record_entries, table_entries) -> None:
    assert set(table_entries) == set(record_entries)


@pytest.mark.parametrize("field", ["language", "intent", "status", "minimum_match_threshold"])
def test_entry_identity_matches_the_record(field, record_entries, table_entries) -> None:
    for reply_id, recorded in record_entries.items():
        assert getattr(table_entries[reply_id], field) == recorded[field], reply_id


def test_no_unapproved_phrasing_is_in_the_table(record_entries, table_entries) -> None:
    """Direction one: nothing may be posted that the document does not approve."""
    for reply_id, recorded in record_entries.items():
        approved = {item["text"] for item in recorded["approved_phrasings"]}
        for phrasing in table_entries[reply_id].approved_phrasings:
            assert phrasing in approved, (
                f"{reply_id}: phrase is not in the approval record, so it was invented "
                f"or reworded:\n{phrasing!r}"
            )


def test_no_approved_phrasing_is_missing_from_the_table(record_entries, table_entries) -> None:
    """Direction two: nothing the document approves may be dropped."""
    for reply_id, recorded in record_entries.items():
        in_table = set(table_entries[reply_id].approved_phrasings)
        for item in recorded["approved_phrasings"]:
            assert item["text"] in in_table, (
                f"{reply_id}: approved text (document line {item['doc_lines']}) is missing "
                f"from the table:\n{item['text']!r}"
            )


def test_every_postable_phrasing_leads_with_its_signed_off_text(record_entries, table_entries) -> None:
    """Row 1 of each entry is the § Sign-off row, verbatim.

    Where the document expands a row by reference ('block as row 1, verbatim') the
    expansion is already resolved in the record, so this compares resolved text.
    """
    for reply_id, recorded in record_entries.items():
        sign_off = recorded["sign_off_text"]
        if sign_off is None:
            continue
        row_1 = table_entries[reply_id].approved_phrasings[0]
        if recorded.get("sign_off_is_reference"):
            assert row_1.startswith(sign_off.split("\n")[0])
        else:
            assert row_1 == sign_off, reply_id


def test_approval_is_what_status_carries_and_calibration_is_not_per_entry(
    record, record_entries, table_entries
) -> None:
    """Approval and calibration are different questions, recorded in different places.

    The sign-off record approves text on a date, so an entry's text is approved or
    there is no text at all to approve. How far a threshold can be trusted is a
    separate matter, and the document states it once for the whole table rather than
    entry by entry -- so a per-entry calibration status must not creep back into
    either file.
    """
    for reply_id, entry in table_entries.items():
        assert entry.status in ('approved', 'escalate'), reply_id
    for reply_id, recorded in record_entries.items():
        assert 'threshold_status' not in recorded, (
            f'{reply_id}: calibration recorded per entry as well as for the table'
        )
    assert record['threshold_status'] == 'provisional', (
        'the record no longer carries the document\'s statement that the numbers are '
        'provisional; if the Router now exists, fix this deliberately'
    )


def test_escalation_only_entries_carry_no_postable_text(record_entries, table_entries) -> None:
    escalation = {rid for rid, entry in record_entries.items() if entry["status"] == "escalate"}
    assert escalation, "the record must name the escalation-only entries"
    for reply_id in escalation:
        assert table_entries[reply_id].approved_phrasings == (), reply_id
        assert table_entries[reply_id].status == "escalate"


def test_intents_with_no_approved_text_have_no_entry_to_post_from(record, table_entries) -> None:
    """The non-postable routing invariants.

    An Intent the document gives no text is not postable, whatever else is true of it,
    and there must be no entry carrying phrasings for it.
    """
    assert set(record["intents_with_no_text"]) == {"HELP_REQUEST", "JOIN_ENQUIRY"}
    for entry in table_entries.values():
        if entry.intent in record["intents_with_no_text"]:
            assert entry.approved_phrasings == (), entry.reply_id
            assert entry.status == "escalate", entry.reply_id


def test_no_variant_in_the_table_was_invented(record_entries, table_entries) -> None:
    """Recognition data is transcription too.

    A `known_variant` never gets posted, so an invented one does not put unapproved
    words in front of anyone -- but it does make the agent answer a Comment the
    document's evidence does not cover. Every variant must be one the document
    records.
    """
    for reply_id, recorded in record_entries.items():
        observed = {item["text"] for item in recorded["known_variants"]}
        for variant in table_entries[reply_id].known_variants:
            assert variant in observed, (
                f"{reply_id}: variant is not in the approval record:\n{variant!r}"
            )


def test_no_recorded_variant_is_missing_from_the_table(record_entries, table_entries) -> None:
    for reply_id, recorded in record_entries.items():
        in_table = set(table_entries[reply_id].known_variants)
        for item in recorded["known_variants"]:
            assert item["text"] in in_table, (
                f"{reply_id}: recorded variant (document line {item['doc_lines']}) is "
                f"missing from the table:\n{item['text']!r}"
            )


def test_recorded_variants_are_quoted_on_the_lines_they_cite(record_entries) -> None:
    """The record's own provenance, checked against the document.

    The record says where each variant came from. If that claim were false the two
    tests above would be checking the table against a fabrication.
    """
    for reply_id, recorded in record_entries.items():
        for item in recorded["known_variants"]:
            cited = [DOCUMENT_LINES[n - 1] for n in item["doc_lines"]]
            assert any(item["text"].lower() in line.lower() for line in cited), (
                f"{reply_id}: variant is not quoted on its cited lines "
                f"{item['doc_lines']}:\n{item['text']!r}"
            )


def test_recorded_phrasings_are_quoted_on_the_lines_they_cite(record_entries) -> None:
    """The record's own provenance for approved text, checked against the document.

    Without this the two directions above would be checking the table against the
    record's word for it. Each recorded phrasing must be *constructible* from the
    document cell it cites: the cell's text with the markdown emphasis and line breaks
    resolved, and -- where the document writes `(block as row 1, verbatim)` rather than
    repeating the bank details -- the block taken from row 1's own cell.
    """
    def cell(doc_line: int) -> str:
        match = re.match(r"^\|\s*\d+\s*\|\s*(.*?)\s*\|\s*$", DOCUMENT_LINES[doc_line - 1])
        assert match, f"line {doc_line} is not a phrasing row: {DOCUMENT_LINES[doc_line - 1]!r}"
        return match.group(1).replace("*", "").replace("`", "").replace("<br>", "\n").strip()

    for reply_id, recorded in record_entries.items():
        phrasings = recorded["approved_phrasings"]
        if not phrasings:
            continue
        row_1_cell = cell(phrasings[0]["doc_lines"][0])
        block = row_1_cell.split("\n\n", 1)[1] if "\n\n" in row_1_cell else ""
        for item in phrasings:
            document_text = cell(item["doc_lines"][0])
            if "(block as row 1, verbatim)" in document_text:
                assert block, f"{reply_id}: row 1 has no block to substitute"
                document_text = document_text.replace("(block as row 1, verbatim)", block)
            assert document_text == item["text"], (
                f"{reply_id}: recorded text does not match document line {item['doc_lines']}\n"
                f"  document: {document_text!r}\n  recorded: {item['text']!r}"
            )


def test_variants_are_cited_from_their_own_entry_section(record_entries) -> None:
    """Provenance has to point into the entry's own section, not merely at some line
    that quotes the same words.

    The document quotes two of these Comments under more than one Intent -- the same
    Comment filed as both `DOA_BLESSING` and `PRAISE_ENCOURAGE` -- so "the quoted text
    appears on a cited line" cannot tell a right filing from a wrong one. Without this,
    a variant could be moved into the wrong entry and cited at the other entry's line
    and every check above would still pass.
    """
    for reply_id, recorded in record_entries.items():
        for item in recorded["known_variants"]:
            owners = {SECTION_OF_LINE[n] for n in item["doc_lines"]}
            assert owners == {reply_id}, (
                f"{reply_id}: variant is cited from {sorted(str(o) for o in owners)}, "
                f"not from its own section:\n{item['text']!r}"
            )


def test_phrasings_are_cited_from_their_own_entry_section(record_entries) -> None:
    """The same invariant for approved text, allowing the document's one shared table.

    `tt-zakat-001` posts the same rows as `tt-donate-001` rather than repeating them,
    which the record marks with `sign_off_is_reference`. That sharing must be exact row
    for row: a by-reference entry that cited another entry's section and then carried
    *different* text would be posting text nobody approved for it.
    """
    for reply_id, recorded in record_entries.items():
        phrasings = recorded["approved_phrasings"]
        if not phrasings:
            continue
        owners = {SECTION_OF_LINE[n] for item in phrasings for n in item["doc_lines"]}
        if not recorded.get("sign_off_is_reference"):
            assert owners == {reply_id}, (
                f"{reply_id}: text is cited from {sorted(str(o) for o in owners)}, "
                f"not from its own section"
            )
            continue
        assert len(owners) == 1, f"{reply_id}: by-reference rows cite several sections"
        referent = next(iter(owners))
        assert referent in record_entries, f"{reply_id}: cites unknown section {referent!r}"
        assert [item["text"] for item in phrasings] == [
            item["text"] for item in record_entries[referent]["approved_phrasings"]
        ], f"{reply_id}: shares {referent}'s rows by reference but does not match them"


def test_every_excluded_string_carries_a_reason_and_a_line(record_entries) -> None:
    """Strings the document names but that must not be recognised are recorded, not dropped."""
    for reply_id, recorded in record_entries.items():
        for item in recorded["variants_not_carried"]:
            assert item["reason"], (reply_id, item["text"])
            assert item["doc_lines"], (reply_id, item["text"])
            assert item["text"] not in {v["text"] for v in recorded.get("known_variants", [])}


def test_bare_formula_exclusions_really_are_bare_formulae(record_entries, table_entries) -> None:
    """The one exclusion reason that is mechanical, so it is machine-checked.

    ADR 0018 sends a bare religious formula to `NO_REPLY` without a Reply, so carrying
    one as a `known_variant` would route it to a postable entry. Every exclusion that
    claims this reason must actually be one.
    """
    checked = 0
    for reply_id, recorded in record_entries.items():
        for item in recorded["variants_not_carried"]:
            if item["reason"] != "bare_formula_is_no_reply_adr_0018":
                continue
            checked += 1
            assert bare_interjection(item["text"]), (
                f"{reply_id}: excluded as a bare formula but is not one:\n{item['text']!r}"
            )
    assert checked, "no bare-formula exclusion was found to check; the record's shape changed"


def test_no_bare_formula_survives_as_a_variant(record_entries) -> None:
    """The same invariant over what the table *does* carry."""
    for reply_id, recorded in record_entries.items():
        for item in recorded["known_variants"]:
            assert not bare_interjection(item["text"]), (
                f"{reply_id}: a bare formula would be recognised and replied to:\n"
                f"{item['text']!r} (normalizes to {normalize(item['text'])!r})"
            )


def test_matching_criteria_matches_the_record_and_verbatim_lines(record_entries, table_entries):
    """`matching_criteria` is the definition text the Router is given; the record
    carries it, its source, and the document line it was read from, so compare all."""
    for reply_id, recorded in record_entries.items():
        assert table_entries[reply_id].matching_criteria == recorded["matching_criteria"], reply_id
        if recorded.get("matching_criteria_source") == "verbatim":
            def compact(text: str) -> str:
                return "".join(text.split()).replace("**", "")
            for number in recorded["matching_criteria_doc_lines"]:
                # The document wraps a single criteria value across lines, so the
                # cited line and its continuation are compared without whitespace.
                window = "".join(DOCUMENT_LINES[number - 1 : number + 1])
                assert compact(recorded["matching_criteria"]) in compact(window), (
                    f"{reply_id}: recorded criteria not found on cited document line {number}"
                )
