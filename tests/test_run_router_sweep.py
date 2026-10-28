"""The network runner's recorder: it records what the client returned, nothing more.

Every fixture Comment here is invented (D16). The one live test is `network`-marked
and skipped unless `OPENROUTER_API_KEY` is set; the rest run offline with a double.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from agent.matching import Decisions
from agent.record import Outcome
from agent.reply_table import load_reply_table
from agent.router import API_KEY_ENV, RouterUnavailable
from tools import run_router_sweep


class FakeClient:
    """A `DecisionsClient` double: a state -> Decisions/None map, or a raise."""

    def __init__(
        self,
        by_state: dict,
        *,
        error: Exception | None = None,
        fail_states: set[str] | None = None,
    ) -> None:
        self.by_state = by_state
        self.error = error
        self.fail_states = fail_states or set()
        self.calls: list[str] = []

    def decide(self, normalized_comment, options):
        self.calls.append(normalized_comment)
        if self.error is not None or normalized_comment in self.fail_states:
            raise self.error or RouterUnavailable("HTTP 503")
        return self.by_state.get(normalized_comment, None)


def _row(nid: str, text: str, label: str) -> dict:
    return {
        "nid": nid,
        "norm": run_router_sweep.normalize(text),
        "text": text,
        "rows": 1,
        "label": label,
        "note": "",
    }


def _read(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_run_sweep_records_one_decision_per_comment(tmp_path):
    table = load_reply_table()
    rows = [
        _row("n-one", "komen satu untuk doa", "DOA_BLESSING"),
        _row("n-two", "komen dua untuk sertai", "JOIN_ENQUIRY"),
    ]
    client = FakeClient(
        {
            rows[0]["norm"]: Decisions(confidences={"tt-doa-001": 0.9}),
            rows[1]["norm"]: None,  # the Router declined: the Tail
        }
    )
    decisions = tmp_path / "decisions.jsonl"

    recorded = run_router_sweep.run_sweep(rows, table, client, decisions_path=decisions)

    assert recorded == 2
    lines = _read(decisions)
    assert [line["nid"] for line in lines] == ["n-one", "n-two"]
    assert lines[0]["kind"] == "choice"
    assert lines[0]["confidences"] == {"tt-doa-001": 0.9}
    assert lines[0]["outcome"] == Outcome.CANNED_REPLY.name
    assert lines[1]["kind"] == "declined"
    assert lines[1]["outcome"] == Outcome.OUT_OF_SCOPE.name


def test_a_variant_hit_is_recorded_as_its_own_kind(tmp_path):
    """A Variant is answered with no Router call and is not a threshold data point."""
    table = load_reply_table()
    rows = [_row("n-variant", "salam", "GREETING")]  # a declared Variant of tt-greet-001
    client = FakeClient({})
    decisions = tmp_path / "decisions.jsonl"

    run_router_sweep.run_sweep(rows, table, client, decisions_path=decisions)

    line = _read(decisions)[0]
    assert line["kind"] == "variant"
    assert client.calls == []  # no Router call at all
    assert line["outcome"] == Outcome.CANNED_REPLY.name


def test_a_failure_is_recorded_as_a_failure_and_never_as_a_decline(tmp_path):
    """D13: a failure resolved to the Tail would corrupt the curve permanently."""
    table = load_reply_table()
    rows = [_row("n-fail", "komen gagal", "DOA_BLESSING")]
    client = FakeClient({}, error=RouterUnavailable("HTTP 500"))
    decisions = tmp_path / "decisions.jsonl"

    with pytest.raises(RouterUnavailable):
        run_router_sweep.run_sweep(rows, table, client, decisions_path=decisions)

    line = _read(decisions)[0]
    assert line["kind"] == "failure"
    assert line["outcome"] is None
    assert "500" in line["failure"]


def test_the_abort_names_the_comment_it_failed_on(tmp_path):
    """D13: a half-run must be diagnosable, so the abort carries the Comment's nid."""
    table = load_reply_table()
    rows = [
        _row("n-good", "komen pertama", "DOA_BLESSING"),
        _row("n-bad", "komen kedua", "DOA_BLESSING"),
    ]
    client = FakeClient(
        {rows[0]["norm"]: Decisions(confidences={"tt-doa-001": 0.9})},
        fail_states={rows[1]["norm"]},
    )
    decisions = tmp_path / "decisions.jsonl"

    with pytest.raises(run_router_sweep.SweepAborted) as caught:
        run_router_sweep.run_sweep(rows, table, client, decisions_path=decisions)

    assert caught.value.nid == "n-bad"
    assert caught.value.position == 2
    assert caught.value.total == 2
    # Still a RouterUnavailable, so a caller that only knows the base class sees it.
    assert isinstance(caught.value, RouterUnavailable)


def test_the_decisions_file_is_appended_as_it_is_written(tmp_path):
    """A crash leaves a readable partial file, so the scorer can call it partial (D12)."""
    table = load_reply_table()
    rows = [
        _row("n-good", "komen pertama", "DOA_BLESSING"),
        _row("n-bad", "komen kedua", "DOA_BLESSING"),
    ]
    client = FakeClient(
        {rows[0]["norm"]: Decisions(confidences={"tt-doa-001": 0.9})},
        fail_states={rows[1]["norm"]},
    )
    decisions = tmp_path / "decisions.jsonl"
    with pytest.raises(RouterUnavailable):
        run_router_sweep.run_sweep(rows, table, client, decisions_path=decisions)

    lines = _read(decisions)
    assert lines[0]["nid"] == "n-good"
    assert lines[0]["kind"] == "choice"
    assert lines[1]["kind"] == "failure"


def test_main_reports_the_abort_on_stderr_naming_the_comment(monkeypatch, tmp_path, capsys):
    """D13: the abort's *message* names the Comment, not just the exception object.

    `main` is where the defect lived: an exception that carries `nid`/`position`
    but is printed as a bare cause is undiagnosable. This drives `main` with a
    client that fails on the second Comment and asserts the stderr message.
    """
    table = load_reply_table()
    rows = [
        _row("n-good", "komen pertama untuk doa", "DOA_BLESSING"),
        _row("n-bad", "komen kedua untuk doa", "DOA_BLESSING"),
    ]
    labelled = tmp_path / "labelled.jsonl"
    labelled.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )
    decisions = tmp_path / "decisions.jsonl"
    journal = tmp_path / "journal.jsonl"

    class _Client:
        base_url = "http://example.invalid"
        model = "test-model"

        def decide(self, normalized_comment, options):
            if normalized_comment == rows[1]["norm"]:
                raise RouterUnavailable("HTTP 503")
            return Decisions(confidences={"tt-doa-001": 0.9})

    monkeypatch.setenv(API_KEY_ENV, "test-key")
    monkeypatch.setattr(run_router_sweep, "OpenRouterDecisions", lambda **kwargs: _Client())

    code = run_router_sweep.main(
        [
            "--labelled",
            str(labelled),
            "--decisions",
            str(decisions),
            "--journal",
            str(journal),
        ]
    )

    err = capsys.readouterr().err
    assert code != 0
    assert "n-bad" in err  # the Comment is named by its nid ...
    assert "2/2" in err  # ... and by its position in the sweep


# --- one opt-in live run, the same shape the ticket's D17 run uses --------------


_LIVE = pytest.mark.skipif(
    not os.environ.get(API_KEY_ENV),
    reason="set OPENROUTER_API_KEY to make the live Router sweep call",
)


@_LIVE
@pytest.mark.network
def test_one_live_sweep_records_a_decision_over_the_options_supplied(tmp_path):
    from agent.router import DecisionJournal, OpenRouterDecisions

    table = load_reply_table()
    rows = [_row("n-live", "saya nak tanya macam mana nak sumbang derma", "DONATION_ENQUIRY")]
    decisions = tmp_path / "decisions.jsonl"
    journal = DecisionJournal(tmp_path / "journal.jsonl")
    client = OpenRouterDecisions(journal=journal)

    run_router_sweep.run_sweep(
        rows, table, client, decisions_path=decisions, journal_path=journal.path
    )

    line = _read(decisions)[0]
    assert line["kind"] in {"choice", "declined", "uncertain"}
    if line["kind"] == "choice":
        offered = {entry.reply_id for entry in table.entries}
        assert set(line["confidences"]) <= offered
