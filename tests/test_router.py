"""Behaviour of the Router seam's real client: the wire call and its outcomes.

No test here touches the network except the one marked `network`, and that one is
skipped unless `OPENROUTER_API_KEY` is set. The transport is a double everywhere
else, so the default suite runs offline (D2, D12).
"""

from __future__ import annotations

import http.client
import json
import os
import re
import ssl
import urllib.error
from pathlib import Path

import pytest

import agent
from agent.matching import Decisions, Matcher
from agent.record import Outcome
from agent.reply_table import load_reply_table
from agent.router import (
    API_KEY_ENV,
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    SENTINEL,
    SENTINEL_CRITERIA,
    DecisionJournal,
    HttpRequest,
    MissingApiKey,
    MissingJournal,
    OpenRouterDecisions,
    RouterUnavailable,
    UrllibTransport,
    build_questions,
)

# A clearly synthetic key. The real key is never written to a fixture; this
# placeholder is what the leak test proves the journal and the body never carry.
SYNTHETIC_KEY = "sk-synthetic-never-stored"

AGENT_DIR = Path(agent.__file__).resolve().parent


class RecordingTransport:
    """A transport double that records the request and replays one body."""

    def __init__(self, body: str) -> None:
        self.body = body
        self.requests: list[HttpRequest] = []

    def __call__(self, request: HttpRequest) -> str:
        self.requests.append(request)
        return self.body


class RaisingTransport:
    """A transport double that fails the way the wire fails (D7)."""

    def __init__(self, error: Exception) -> None:
        self.error = error

    def __call__(self, request: HttpRequest) -> str:
        raise self.error


def _reply_body(
    choice: object,
    probabilities: dict,
    *,
    type: str = "choice",
    usage: dict | None = None,
) -> str:
    """A response body in the measured shape."""
    return json.dumps(
        {
            "model": DEFAULT_MODEL + "-20261014",
            "answers": {
                "reply": {
                    "type": type,
                    "choice": choice,
                    "confidence": 0.98,
                    "probabilities": probabilities,
                }
            },
            "usage": usage if usage is not None else {"input_tokens": 371, "output_tokens": 59, "cost": 1.5582e-05},
            "id": "gen-dec-test",
            "provider": "TypeSafe",
        }
    )


@pytest.fixture
def journal(tmp_path) -> DecisionJournal:
    """A real journal, because the client refuses to exist without one (AC 4).

    Every construction in this file names one, the way a call site must: a helper
    that quietly defaulted one would repeat the defect this fixture exists to keep
    out of the suite.
    """
    return DecisionJournal(tmp_path / "decisions.jsonl")


def _client(transport, *, journal, monkeypatch, **overrides) -> OpenRouterDecisions:
    """The client under test, always handed a journal -- as a call site must be."""
    monkeypatch.setenv(API_KEY_ENV, SYNTHETIC_KEY)
    return OpenRouterDecisions(transport=transport, journal=journal, **overrides)


# --- AC 1: the Router is the only place a model is called ----------------------


def test_urllib_request_is_imported_only_by_the_router() -> None:
    """The mechanical half of AC 1: one module dials out, and it is `router.py`.

    `urllib.request`, `http.client` and `socket` are the outbound-network modules;
    `http.server`, `socketserver` and `urllib.parse` (used by the Recorded page)
    are not, and the module boundary is matched precisely so they do not trip it.
    `router.py` carries both of its entries for the failure mapping: `urllib.request`
    for the call, `http.client` for the errors a call can raise (D7).
    """
    offenders: dict[str, list[str]] = {}
    for path in AGENT_DIR.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        found = [
            module
            for module in ("urllib.request", "http.client", "socket")
            if re.search(rf"^\s*(?:import|from)\s+{re.escape(module)}\b", text, re.M)
        ]
        if found:
            offenders[path.name] = found
    assert offenders == {"router.py": ["urllib.request", "http.client"]}, offenders


# --- AC 2/3/5: a typed choice over the options, never text ---------------------


def test_the_router_returns_a_typed_choice_over_the_entries_supplied(monkeypatch, journal) -> None:
    table = load_reply_table()
    transport = RecordingTransport(
        _reply_body(
            "tt-donate-001",
            {"tt-donate-001": 0.99, "tt-join-001": 0.0, SENTINEL: 0.01},
        )
    )
    client = _client(transport, journal=journal, monkeypatch=monkeypatch)

    result = client.decide("a comment asking how to donate", table.entries)

    assert isinstance(result, Decisions)
    assert not result.uncertain
    assert result.confidences["tt-donate-001"] == 0.99


def test_the_sentinel_key_never_reaches_the_returned_confidences(monkeypatch, journal) -> None:
    table = load_reply_table()
    transport = RecordingTransport(
        _reply_body(
            "tt-donate-001",
            {"tt-donate-001": 0.99, "tt-join-001": 0.0, SENTINEL: 0.01},
        )
    )
    client = _client(transport, journal=journal, monkeypatch=monkeypatch)

    result = client.decide("a comment asking how to donate", table.entries)

    assert SENTINEL not in result.confidences
    assert set(result.confidences) <= {entry.reply_id for entry in table.entries}


def test_the_answer_carries_no_text_of_its_own(monkeypatch, journal) -> None:
    """An extra text field on the wire answer is ignored, not returned."""
    table = load_reply_table()
    body = json.loads(
        _reply_body(
            "tt-greet-001",
            {"tt-greet-001": 0.9, SENTINEL: 0.1},
        )
    )
    body["answers"]["reply"]["text"] = "an invented reply the Router must not return"
    client = _client(RecordingTransport(json.dumps(body)), journal=journal, monkeypatch=monkeypatch)

    result = client.decide("salam", table.entries)

    assert isinstance(result, Decisions)
    assert "invented" not in json.dumps(result.confidences)


# --- D1: the contract is configuration ----------------------------------------


def test_the_base_url_default_avoids_the_api_v1_trap(monkeypatch, journal) -> None:
    """The spec's `/api/v1` composition 404s; the default must never carry it."""
    assert DEFAULT_BASE_URL == "https://openrouter.ai/api/alpha/decisions"
    assert "/api/v1" not in DEFAULT_BASE_URL

    table = load_reply_table()
    transport = RecordingTransport(_reply_body(SENTINEL, {SENTINEL: 1.0}))
    client = _client(transport, journal=journal, monkeypatch=monkeypatch)
    client.decide("anything", table.entries)
    assert "/api/v1" not in transport.requests[0].url
    assert transport.requests[0].url == DEFAULT_BASE_URL


def test_the_model_id_is_configuration_not_a_constant(monkeypatch, journal) -> None:
    table = load_reply_table()
    transport = RecordingTransport(_reply_body(SENTINEL, {SENTINEL: 1.0}))
    client = _client(
        transport, journal=journal, monkeypatch=monkeypatch, model="another/decision-model"
    )

    client.decide("anything", table.entries)

    assert json.loads(transport.requests[0].body)["model"] == "another/decision-model"


# --- D3: the key comes from the environment and stays there --------------------


def test_a_missing_key_refuses_loudly_at_construction(monkeypatch, journal) -> None:
    monkeypatch.delenv(API_KEY_ENV, raising=False)
    with pytest.raises(MissingApiKey, match=API_KEY_ENV):
        OpenRouterDecisions(journal=journal)


def test_a_client_with_no_journal_is_refused(monkeypatch) -> None:
    """AC 4 says *every* decision records, so a journalless client cannot exist.

    Without this, the guarantee is opt-in: ``OpenRouterDecisions()`` constructed
    happily, ``decide`` recorded nowhere, and nothing complained -- AC 4 silently
    unmet for any caller who did not think about it.
    """
    monkeypatch.setenv(API_KEY_ENV, SYNTHETIC_KEY)
    with pytest.raises(MissingJournal, match="decision journal"):
        OpenRouterDecisions(journal=None)


def test_the_key_never_reaches_the_body_or_the_journal(monkeypatch, tmp_path) -> None:
    table = load_reply_table()
    journal = DecisionJournal(tmp_path / "decisions.jsonl")
    transport = RecordingTransport(
        _reply_body("tt-greet-001", {"tt-greet-001": 0.9, SENTINEL: 0.1})
    )
    client = _client(transport, journal=journal, monkeypatch=monkeypatch)

    client.decide("salam", table.entries)

    body = transport.requests[0].body
    assert SYNTHETIC_KEY.encode("utf-8") not in body
    assert SYNTHETIC_KEY not in journal.path.read_text(encoding="utf-8")
    # The key is not lost, it is in the header, which is where a bearer token goes.
    assert transport.requests[0].headers["Authorization"] == f"Bearer {SYNTHETIC_KEY}"


# --- D4: the options are exactly the entries handed in -------------------------


def test_every_entry_is_offered_in_order_with_its_own_criteria(monkeypatch, journal) -> None:
    table = load_reply_table()
    transport = RecordingTransport(_reply_body(SENTINEL, {SENTINEL: 1.0}))
    client = _client(transport, journal=journal, monkeypatch=monkeypatch)

    client.decide("the normalized comment", table.entries)

    payload = json.loads(transport.requests[0].body)
    assert payload["state"] == "the normalized comment"
    criteria = payload["questions"]["reply"]["criteria"]
    assert list(criteria) == [entry.reply_id for entry in table.entries] + [SENTINEL]
    for entry in table.entries:
        assert criteria[entry.reply_id] == entry.matching_criteria
    assert criteria[SENTINEL] == SENTINEL_CRITERIA
    assert payload["questions"]["reply"]["type"] == "choice"


# --- D5: the Tail is a model choice --------------------------------------------


def test_a_sentinel_pick_is_the_tail_and_not_a_decision(monkeypatch, journal) -> None:
    table = load_reply_table()
    transport = RecordingTransport(
        _reply_body(SENTINEL, {"tt-praise-001": 0.0, SENTINEL: 1.0})
    )
    client = _client(transport, journal=journal, monkeypatch=monkeypatch)

    assert client.decide("Cantiknya gambar ni, semoga berjaya semua", table.entries) is None


def test_a_sentinel_pick_reaches_the_matcher_as_the_out_of_scope_tail(monkeypatch, journal) -> None:
    table = load_reply_table()
    transport = RecordingTransport(
        _reply_body(SENTINEL, {"tt-praise-001": 0.0, SENTINEL: 1.0})
    )
    client = _client(transport, journal=journal, monkeypatch=monkeypatch)
    matcher = Matcher(table, client)

    result = matcher.match_comment("Cantiknya gambar ni, semoga berjaya semua")

    assert result.entry is None
    assert result.outcome is Outcome.OUT_OF_SCOPE


# --- D6: what makes a reading uncertain ----------------------------------------


def test_a_non_choice_answer_is_uncertain(monkeypatch, journal) -> None:
    table = load_reply_table()
    transport = RecordingTransport(
        _reply_body("tt-greet-001", {"tt-greet-001": 0.9}, type="categorical")
    )
    client = _client(transport, journal=journal, monkeypatch=monkeypatch)

    result = client.decide("salam", table.entries)

    assert result.uncertain
    assert result.confidences == {}


def test_an_answer_with_no_probabilities_is_uncertain_not_a_tail(monkeypatch, journal) -> None:
    table = load_reply_table()
    transport = RecordingTransport(_reply_body("tt-greet-001", {}))
    client = _client(transport, journal=journal, monkeypatch=monkeypatch)

    result = client.decide("salam", table.entries)

    assert result is not None
    assert result.uncertain
    assert result.confidences == {}


def test_a_chosen_value_outside_the_options_is_uncertain(monkeypatch, journal) -> None:
    """A chosen value the Router was not offered is refused, not silently used.

    The probabilities matter here: an unoffered ``choice`` alongside a *supplied*
    entry at 0.9 is the case where dropping the validation would post a reply the
    Router never chose. With an unoffered id as the only candidate, the mutation
    still lands on ``uncertain`` -- via the empty-confidences path, for the wrong
    reason -- so this body is what makes the guarantee real.
    """
    table = load_reply_table()
    transport = RecordingTransport(
        _reply_body("tt-not-offered", {"tt-greet-001": 0.9, "tt-not-offered": 0.05})
    )
    client = _client(transport, journal=journal, monkeypatch=monkeypatch)

    result = client.decide("salam", table.entries)

    assert result.uncertain
    assert result.confidences == {}


def test_a_body_that_is_not_a_json_object_is_uncertain_not_a_tail(monkeypatch, journal) -> None:
    """A JSON array (or a bare string) is a malformed answer, not the Tail (D6)."""
    table = load_reply_table()
    client = _client(RecordingTransport('["not", "an", "object"]'), journal=journal, monkeypatch=monkeypatch)

    result = client.decide("salam", table.entries)

    assert result is not None
    assert result.uncertain


def test_a_probability_that_is_not_a_number_is_uncertain(monkeypatch, journal) -> None:
    table = load_reply_table()
    transport = RecordingTransport(_reply_body("tt-greet-001", {"tt-greet-001": "high"}))
    client = _client(transport, journal=journal, monkeypatch=monkeypatch)

    result = client.decide("salam", table.entries)

    assert result.uncertain


def test_an_uncertain_reading_escalates_and_never_reaches_a_reply(monkeypatch, journal) -> None:
    table = load_reply_table()
    transport = RecordingTransport(
        _reply_body("tt-greet-001", {"tt-greet-001": 0.99}, type="categorical")
    )
    client = _client(transport, journal=journal, monkeypatch=monkeypatch)
    matcher = Matcher(table, client)

    result = matcher.match_comment("a comment only the Router decides")

    assert result.entry is None
    assert result.outcome is Outcome.UNCERTAIN


# --- D7: a failure is not a decision -------------------------------------------


def test_a_transport_failure_raises_and_is_not_a_tail(monkeypatch, journal) -> None:
    table = load_reply_table()
    transport = RaisingTransport(RouterUnavailable("the Router answered HTTP 402"))
    client = _client(transport, journal=journal, monkeypatch=monkeypatch)

    with pytest.raises(RouterUnavailable, match="402"):
        client.decide("a comment asking for help", table.entries)


def test_a_402_is_never_recorded_as_the_out_of_scope_tail(monkeypatch, journal) -> None:
    table = load_reply_table()
    transport = RaisingTransport(RouterUnavailable("HTTP 402 in_flight_budget_exhausted"))
    client = _client(transport, journal=journal, monkeypatch=monkeypatch)
    matcher = Matcher(table, client)

    with pytest.raises(RouterUnavailable):
        matcher.match_comment("a comment asking for help")


def test_unparseable_json_raises_rather_than_becoming_a_tail(monkeypatch, journal) -> None:
    table = load_reply_table()
    client = _client(RecordingTransport("<html>not json</html>"), journal=journal, monkeypatch=monkeypatch)

    with pytest.raises(RouterUnavailable):
        client.decide("anything", table.entries)


def test_the_urllib_transport_maps_http_errors_to_router_unavailable() -> None:
    """The real transport's failure mapping, proven offline with a fake opener."""

    def opener(request, timeout=None):
        raise urllib.error.HTTPError(request.full_url, 402, "Payment Required", {}, None)

    transport = UrllibTransport(opener=opener)
    with pytest.raises(RouterUnavailable, match="402"):
        transport(HttpRequest(url="https://example.test", headers={}, body=b"{}"))


class _FailingRead:
    """A response whose body stops early -- the mid-read failure."""

    def __enter__(self) -> "_FailingRead":
        return self

    def __exit__(self, *exc) -> bool:
        return False

    def read(self) -> bytes:
        raise ConnectionResetError("reset mid-read")


@pytest.mark.parametrize(
    "error",
    [
        urllib.error.URLError("no route to host"),
        TimeoutError("timed out"),
        ConnectionResetError("reset by peer"),
        ssl.SSLError("handshake failed"),
        http.client.RemoteDisconnected("remote closed"),
        http.client.IncompleteRead(b"1", 5),
        http.client.BadStatusLine("junk"),
    ],
    ids=lambda error: type(error).__name__,
)
def test_the_urllib_transport_types_every_way_the_wire_fails(error) -> None:
    """Every failure is a `RouterUnavailable`, so `decide` can record it (D7, D8).

    A connection reset, a failed handshake, a body that stops early and a
    malformed status line are the ordinary ways a call dies. Left untranslated,
    each escapes `decide`'s `except` clauses -- which skips the journal entry as
    well, breaking D7 and D8 together.
    """

    def opener(request, timeout=None):
        raise error

    transport = UrllibTransport(opener=opener)
    with pytest.raises(RouterUnavailable):
        transport(HttpRequest(url="https://example.test", headers={}, body=b"{}"))


def test_the_urllib_transport_types_a_failure_that_happens_while_reading() -> None:
    """The read is inside the guarded block, not just the call (D7)."""
    transport = UrllibTransport(opener=lambda request, timeout=None: _FailingRead())

    with pytest.raises(RouterUnavailable, match="reset mid-read"):
        transport(HttpRequest(url="https://example.test", headers={}, body=b"{}"))


def test_a_transport_that_breaks_its_contract_is_still_recorded_and_typed(monkeypatch, journal) -> None:
    """D8's backstop: the single-entry guarantee cannot rest on a transport's care.

    `Transport`'s contract is to raise `RouterUnavailable`, but a transport (or a
    double) that raises anything else must not skip the journal -- "every decision
    gets exactly one entry" is a property of the client, not of its collaborators.
    """
    table = load_reply_table()
    client = _client(
        RaisingTransport(RuntimeError("a transport that breaks its contract")),
        journal=journal,
        monkeypatch=monkeypatch,
    )

    with pytest.raises(RouterUnavailable, match="breaks its contract"):
        client.decide("anything", table.entries)

    entries = [json.loads(line) for line in journal.path.read_text(encoding="utf-8").splitlines()]
    assert len(entries) == 1
    assert "breaks its contract" in entries[0]["failure"]


def test_the_urllib_transport_normalises_a_timeout_to_router_unavailable() -> None:
    def opener(request, timeout=None):
        raise TimeoutError("timed out")

    transport = UrllibTransport(opener=opener)
    with pytest.raises(RouterUnavailable):
        transport(HttpRequest(url="https://example.test", headers={}, body=b"{}"))


# --- D8: the decision journal --------------------------------------------------


def test_a_chosen_decision_is_legible_in_the_journal_after_the_fact(monkeypatch, tmp_path) -> None:
    table = load_reply_table()
    journal = DecisionJournal(tmp_path / "decisions.jsonl")
    transport = RecordingTransport(
        _reply_body(
            "tt-donate-001",
            {"tt-donate-001": 0.99, "tt-join-001": 0.0, SENTINEL: 0.01},
            usage={"input_tokens": 371, "output_tokens": 59, "cost": 1.5582e-05},
        )
    )
    client = _client(transport, journal=journal, monkeypatch=monkeypatch)

    client.decide("a comment asking how to donate", table.entries)

    entries = [json.loads(line) for line in journal.path.read_text(encoding="utf-8").splitlines()]
    assert len(entries) == 1
    entry = entries[0]
    assert entry["chosen"] == "tt-donate-001"
    assert entry["probabilities"][SENTINEL] == 0.01
    assert entry["uncertain"] is False
    assert entry["failure"] is None
    assert entry["usage"]["cost"] == 1.5582e-05
    assert entry["state"] == "a comment asking how to donate"
    assert entry["model"] == DEFAULT_MODEL


def test_every_decision_gets_exactly_one_journal_entry(monkeypatch, tmp_path) -> None:
    table = load_reply_table()
    journal = DecisionJournal(tmp_path / "decisions.jsonl")
    transport = RecordingTransport(_reply_body("tt-greet-001", {"tt-greet-001": 0.9, SENTINEL: 0.1}))
    client = _client(transport, journal=journal, monkeypatch=monkeypatch)

    client.decide("a chosen comment", table.entries)
    transport.body = _reply_body("tt-greet-001", {"tt-greet-001": 0.99}, type="categorical")
    client.decide("an uncertain comment", table.entries)
    transport.body = _reply_body(SENTINEL, {SENTINEL: 1.0})
    client.decide("a tail comment", table.entries)
    failing = _client(RaisingTransport(RouterUnavailable("HTTP 500")), journal=journal, monkeypatch=monkeypatch)
    with pytest.raises(RouterUnavailable):
        failing.decide("a failed comment", table.entries)

    entries = [json.loads(line) for line in journal.path.read_text(encoding="utf-8").splitlines()]
    assert len(entries) == 4
    assert [entry["state"] for entry in entries] == [
        "a chosen comment",
        "an uncertain comment",
        "a tail comment",
        "a failed comment",
    ]
    assert entries[1]["uncertain"] is True
    assert entries[2]["chosen"] == SENTINEL
    assert "500" in entries[3]["failure"]


def test_the_journal_file_is_owner_only(monkeypatch, tmp_path) -> None:
    journal = DecisionJournal(tmp_path / "decisions.jsonl")
    journal.append({"anything": True})
    assert (journal.path.stat().st_mode & 0o777) == 0o600


# --- D9: determinism is a property of the request ------------------------------


def test_two_identical_items_produce_a_byte_identical_body_with_no_sampling_field(monkeypatch, journal) -> None:
    table = load_reply_table()
    transport = RecordingTransport(_reply_body(SENTINEL, {SENTINEL: 1.0}))
    client = _client(transport, journal=journal, monkeypatch=monkeypatch)

    client.decide("the same comment", table.entries)
    client.decide("the same comment", table.entries)

    first, second = transport.requests
    assert first.body == second.body
    text = first.body.decode("utf-8")
    for field in ("temperature", "top_p", "top_k", "seed", "presence_penalty", "frequency_penalty"):
        assert field not in text


# --- D11: the question builder is additive -------------------------------------


def test_the_question_builder_takes_the_options_and_names_one_question() -> None:
    table = load_reply_table()
    questions = build_questions(table.entries)
    assert set(questions) == {"reply"}, "the deferred second question must not be added here"
    assert questions["reply"]["criteria"][table.entries[0].reply_id] == table.entries[0].matching_criteria


# --- D12: one opt-in live call -------------------------------------------------

_LIVE = pytest.mark.skipif(
    not os.environ.get(API_KEY_ENV),
    reason="set OPENROUTER_API_KEY to make the one live Router call",
)


@_LIVE
@pytest.mark.network
def test_one_live_call_returns_a_typed_choice_over_the_options_supplied(tmp_path) -> None:
    table = load_reply_table()
    journal = DecisionJournal(tmp_path / "live.jsonl")
    client = OpenRouterDecisions(journal=journal)
    options = {entry.reply_id for entry in table.entries}

    print(f"\nlive call -> {client.base_url} model={client.model}")
    result = client.decide("saya nak tanya macam mana nak sumbang derma kepada organisasi ini", table.entries)
    print("journal line: " + journal.path.read_text(encoding="utf-8").strip())

    assert isinstance(result, Decisions), "the live call must return a typed choice, or raise"
    assert not result.uncertain
    assert result.confidences
    assert set(result.confidences) <= options
