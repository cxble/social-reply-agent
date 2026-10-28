"""The offline scorer: it decides nothing, and its inputs resolve from the root.

Every fixture Comment here is invented. The real labelled set is gitignored and
must never appear in a committed file (D16), so nothing under `tests/` reads it.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools import score_threshold


def _row(nid: str, text: str, label: str, rows: int = 1) -> dict:
    return {
        "nid": nid,
        "norm": score_threshold.normalize(text),
        "text": text,
        "rows": rows,
        "label": label,
        "note": "",
    }


def _decision(
    nid: str,
    state: str,
    kind: str,
    *,
    confidences: dict | None = None,
    uncertain: bool = False,
    outcome: str | None = None,
) -> dict:
    return {
        "nid": nid,
        "state": state,
        "kind": kind,
        "confidences": confidences or {},
        "uncertain": uncertain,
        "chosen": None,
        "probabilities": {},
        "failure": None,
        "outcome": outcome,
        "detail": "",
    }


def _write_jsonl(path: Path, records: list[dict]) -> Path:
    path.write_text(
        "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n",
        encoding="utf-8",
    )
    return path


@pytest.fixture
def fixtures(tmp_path: Path) -> tuple[Path, list[dict], list[dict], Path]:
    """Invented labelled rows and decisions, and the files that carry them."""
    rows = [
        _row("n-greet", "komen sapaan mesra", "GREETING", rows=3),
        _row("n-noreply", "komen kosong tanpa apa apa", "NO_REPLY", rows=2),
        _row("n-tail", "komen takziah untuk arwah", "OUT_OF_SCOPE", rows=5),
        _row("n-join", "komen tanya boleh sertai", "JOIN_ENQUIRY", rows=1),
        _row("n-declined", "komen doa yang ditolak", "DOA_BLESSING", rows=4),
    ]
    records = [
        # A correct reply: posts GREETING to a GREETING.
        _decision("n-greet", rows[0]["norm"], "choice", confidences={"tt-greet-001": 0.9}),
        # Posts into silence, NO_REPLY class.
        _decision("n-noreply", rows[1]["norm"], "choice", confidences={"tt-greet-001": 0.9}),
        # Posts into silence, OUT_OF_SCOPE class.
        _decision("n-tail", rows[2]["norm"], "choice", confidences={"tt-praise-001": 0.8}),
        # A money reply posted to an Escalation gate.
        _decision("n-join", rows[3]["norm"], "choice", confidences={"tt-donate-001": 0.95}),
        # Declined: a replyable gold Comment the Router refused (the Tail).
        _decision("n-declined", rows[4]["norm"], "declined"),
    ]
    labelled = _write_jsonl(tmp_path / "labelled.jsonl", rows)
    decisions = _write_jsonl(tmp_path / "decisions.jsonl", records)
    return labelled, rows, records, decisions


def _run(capsys, labelled: Path, decisions: Path) -> tuple[int, str]:
    code = score_threshold.main(
        ["--labelled", str(labelled), "--decisions", str(decisions)]
    )
    return code, capsys.readouterr().out


# --- AC 6: inputs resolve from the repository root, not the working directory ---


def test_default_inputs_are_rooted_at_the_repo_root_not_the_cwd():
    expected_labelled = score_threshold.REPO_ROOT / "data" / "candidates" / "random.labelled.jsonl"
    expected_decisions = score_threshold.REPO_ROOT / "data" / "candidates" / "router.decisions.jsonl"
    assert score_threshold.DEFAULT_LABELLED == expected_labelled
    assert score_threshold.DEFAULT_DECISIONS == expected_decisions
    assert score_threshold.DEFAULT_LABELLED.is_absolute()


def test_the_tool_runs_from_a_directory_that_is_not_the_repo_root(
    monkeypatch, tmp_path, capsys, fixtures
):
    labelled, _, _, decisions = fixtures
    monkeypatch.setattr(score_threshold, "DEFAULT_LABELLED", labelled)
    monkeypatch.setattr(score_threshold, "DEFAULT_DECISIONS", decisions)
    monkeypatch.chdir(tmp_path)

    assert score_threshold.main([]) == 0
    assert "should get a Canned reply" in capsys.readouterr().out


def test_a_missing_input_is_reported_as_missing_and_nothing_else(
    monkeypatch, tmp_path, capsys
):
    missing = tmp_path / "no-such-labelled-file.jsonl"
    monkeypatch.setattr(score_threshold, "DEFAULT_LABELLED", missing)
    monkeypatch.setattr(score_threshold, "DEFAULT_DECISIONS", tmp_path / "d.jsonl")

    assert score_threshold.main([]) == 2
    err = capsys.readouterr().err
    assert str(missing) in err
    assert "missing" in err.lower()
    # The removed advice is wrong: rebuilding needs corpus.jsonl and the hand
    # TSVs, neither of which is in the repo (D11).
    assert "apply_labels" not in err
    assert "rebuild" not in err.lower()


def test_a_missing_decisions_file_is_reported_as_missing(tmp_path, capsys, fixtures):
    labelled, _, _, _ = fixtures
    missing = tmp_path / "no-such-decisions.jsonl"
    assert score_threshold.main(["--labelled", str(labelled), "--decisions", str(missing)]) == 2
    err = capsys.readouterr().err
    assert str(missing) in err
    assert "apply_labels" not in err


# --- D1: the scorer decides nothing; every Outcome comes from `Matcher` --------


def test_a_below_threshold_confidence_is_refused_not_posted(fixtures):
    """A naive argmax would post at 0.30; `Matcher` refuses it, and so does the scorer."""
    labelled, rows, _, decisions = fixtures
    table = score_threshold.load_reply_table()
    # tt-greet-001 sits at 0.80, so 0.30 is below its own number.
    records = [
        _decision("n-greet", rows[0]["norm"], "choice", confidences={"tt-greet-001": 0.30})
    ]
    results = score_threshold.replay_all(
        [rows[0]], records, table
    )
    assert results["n-greet"].outcome is score_threshold.Outcome.BELOW_MINIMUM_MATCH_THRESHOLD


def test_two_intents_above_threshold_conflict_rather_than_taking_the_higher(fixtures):
    labelled, rows, _, decisions = fixtures
    table = score_threshold.load_reply_table()
    records = [
        _decision(
            "n-greet",
            rows[0]["norm"],
            "choice",
            confidences={"tt-greet-001": 0.9, "tt-thanks-001": 0.95},
        )
    ]
    results = score_threshold.replay_all([rows[0]], records, table)
    assert results["n-greet"].outcome is score_threshold.Outcome.CONFLICTING_INTENTS


def test_the_reported_figures_track_matcher_in_both_error_directions(fixtures):
    """D1: the figures follow `Matcher`'s Outcome, not a re-derived rule.

    Two directions a re-implementation would get wrong: a gold-replyable Comment
    *below* its own threshold (0.70 clears the 0.50 floor but not `tt-greet-001`'s
    0.80) must be refused and must not count as covered; a gold-`NO_REPLY` Comment
    *above* it must land in false-on-silence and never in precision. Asserting the
    figures `bucket_figures` returns -- not a second run of the same code -- is what
    makes this bite.
    """
    labelled, rows, _, decisions = fixtures
    table = score_threshold.load_reply_table()
    greet, noreply = rows[0], rows[1]  # gold GREETING (replyable), gold NO_REPLY
    records = [
        # Below tt-greet-001's own 0.80: `Matcher` refuses it, so it is not covered.
        _decision("n-greet", greet["norm"], "choice", confidences={"tt-greet-001": 0.70}),
        # Above 0.80 and gold NO_REPLY: a post into silence, never precision.
        _decision("n-noreply", noreply["norm"], "choice", confidences={"tt-greet-001": 0.95}),
    ]
    results = score_threshold.replay_all([greet, noreply], records, table)
    assert results["n-greet"].outcome is score_threshold.Outcome.BELOW_MINIMUM_MATCH_THRESHOLD
    kind_by_nid = {record["nid"]: record["kind"] for record in records}
    scored = score_threshold._scored([greet, noreply], results, kind_by_nid)
    weights = {greet["nid"]: greet["rows"], noreply["nid"]: noreply["rows"]}
    figures = score_threshold.bucket_figures(
        scored, weights, score_threshold.replyable_intents(table)
    )
    # The refused replyable Comment is not a coverage hit and not posted.
    assert figures["replyable_pop"] == ["n-greet"]
    assert figures["covered"] == []
    assert figures["coverage"] == 0.0
    assert "n-greet" not in figures["posted"]
    # The gold NO_REPLY Comment is the false reply on silence, and is not precision.
    assert figures["silence"] == ["n-noreply"]
    assert "n-noreply" not in figures["right"] + figures["wrong_intent"]


def test_a_file_recorded_at_an_earlier_table_is_reported_as_stale(capsys, fixtures):
    labelled, rows, records, decisions = fixtures
    records[0]["outcome"] = "BELOW_MINIMUM_MATCH_THRESHOLD"  # a lie
    decisions = _write_jsonl(decisions, records)
    _, out = _run(capsys, labelled, decisions)
    assert "decisions recorded at an earlier table (recorded outcome != replayed): 1" in out


# --- D4/AC 2: a declined Comment is a refusal, never a post --------------------


def test_a_declined_replyable_comment_is_not_posted(fixtures):
    """D4: a gold-replyable Comment the Router declined is a refusal, never a post.

    The fixture's `n-declined` is gold `DOA_BLESSING` (replyable) and the Router
    declined it, so it replays as `OUT_OF_SCOPE`. A scorer that counted a
    gold-replyable `OUT_OF_SCOPE` as covered would post a reply nobody chose; this
    asserts the reported figures say it was not covered and not posted.
    """
    labelled, rows, records, decisions = fixtures
    table = score_threshold.load_reply_table()
    results = score_threshold.replay_all(rows, records, table)
    assert results["n-declined"].outcome is score_threshold.Outcome.OUT_OF_SCOPE
    kind_by_nid = {record["nid"]: record["kind"] for record in records}
    scored = score_threshold._scored(rows, results, kind_by_nid)
    weights = {row["nid"]: row["rows"] for row in rows}
    figures = score_threshold.bucket_figures(
        scored, weights, score_threshold.replyable_intents(table)
    )
    # The declined gold-replyable Comment is not covered and not in the posted set.
    assert "n-declined" not in figures["covered"]
    assert "n-declined" not in figures["posted"]


# --- D5/AC 3: the silence bucket is exactly two classes, both kept -------------


def test_false_replies_on_silence_keep_both_classes(fixtures):
    labelled, rows, records, decisions = fixtures
    table = score_threshold.load_reply_table()
    results = score_threshold.replay_all(rows, records, table)
    kind_by_nid = {record["nid"]: record["kind"] for record in records}
    scored = score_threshold._scored(rows, results, kind_by_nid)
    weights = {row["nid"]: row["rows"] for row in rows}
    figures = score_threshold.bucket_figures(
        scored, weights, score_threshold.replyable_intents(table)
    )
    assert set(figures["silence"]) == {"n-noreply", "n-tail"}
    assert figures["silence_noreply"] == ["n-noreply"]
    assert figures["silence_tail"] == ["n-tail"]


# --- D6: an Escalation gate is never scored as a correct reply -----------------


def test_a_gold_join_enquiry_is_not_a_correct_reply(fixtures):
    labelled, rows, records, decisions = fixtures
    table = score_threshold.load_reply_table()
    results = score_threshold.replay_all(rows, records, table)
    kind_by_nid = {record["nid"]: record["kind"] for record in records}
    scored = score_threshold._scored(rows, results, kind_by_nid)
    weights = {row["nid"]: row["rows"] for row in rows}
    figures = score_threshold.bucket_figures(
        scored, weights, score_threshold.replyable_intents(table)
    )
    assert "n-join" not in figures["right"]
    assert figures["gate"] == ["n-join"]


def test_join_enquiry_is_not_in_the_replyable_intents(fixtures):
    table = score_threshold.load_reply_table()
    replyable = score_threshold.replyable_intents(table)
    assert "JOIN_ENQUIRY" not in replyable
    assert "HELP_REQUEST" not in replyable
    assert "DOA_BLESSING" in replyable


# --- D12/D13: a partial run and a failure are visible, never scored as silence --


def test_a_failure_is_reported_and_never_scored_as_a_tail(capsys, fixtures):
    labelled, rows, records, decisions = fixtures
    records = records + [_decision("n-failed", "komen gagal", "failure")]
    rows = rows + [_row("n-failed", "komen gagal", "DOA_BLESSING")]
    labelled = _write_jsonl(labelled, rows)
    decisions = _write_jsonl(decisions, records)
    _, out = _run(capsys, labelled, decisions)
    assert "failures (a failure is not a decision): 1" in out
    table = score_threshold.load_reply_table()
    results = score_threshold.replay_all(rows, records, table)
    kind_by_nid = {record["nid"]: record["kind"] for record in records}
    scored = score_threshold._scored(rows, results, kind_by_nid)
    assert "n-failed" not in {row["nid"] for row, _ in scored}


def test_a_missing_decision_is_reported_as_an_incomplete_run(capsys, fixtures):
    labelled, rows, records, decisions = fixtures
    # Drop one Comment's decision: the Router was never asked about it.
    records = [record for record in records if record["nid"] != "n-noreply"]
    decisions = _write_jsonl(decisions, records)
    _, out = _run(capsys, labelled, decisions)
    assert "labelled Comments with no recorded decision (incomplete run): 1" in out
    assert "INCOMPLETE" in out


def test_a_decision_for_an_unknown_comment_is_reported_as_stale(capsys, fixtures):
    labelled, rows, records, decisions = fixtures
    records = records + [_decision("n-ghost", "komen hantu", "declined")]
    decisions = _write_jsonl(decisions, records)
    _, out = _run(capsys, labelled, decisions)
    assert "decisions naming a Comment not in the labelled set (stale): 1" in out


# --- D1: `with_threshold` *is* the pipeline; a point on the curve is not a model --


def test_with_threshold_moves_a_comment_across_the_bar(fixtures):
    """D1: `with_threshold(table, t)` substitutes the number; the curve is not a no-op.

    A confidence that posts at a low `t` must be refused at a high `t`, and the
    shipped table's own number must be what the un-substituted table gives -- so a
    `with_threshold` that returned the entries unchanged would fail both.
    """
    labelled, rows, _, decisions = fixtures
    table = score_threshold.load_reply_table()
    greet = rows[0]  # gold GREETING; tt-greet-001 sits at 0.80
    records = [
        _decision("n-greet", greet["norm"], "choice", confidences={"tt-greet-001": 0.60})
    ]

    low = score_threshold.replay_all(
        [greet], records, score_threshold.with_threshold(table, 0.50)
    )
    high = score_threshold.replay_all(
        [greet], records, score_threshold.with_threshold(table, 0.90)
    )
    shipped = score_threshold.replay_all([greet], records, table)
    own = score_threshold.replay_all(
        [greet], records, score_threshold.with_threshold(table, 0.80)
    )

    # 0.60 clears 0.50 and is refused by 0.90: the number moved the Comment.
    assert low["n-greet"].outcome is score_threshold.Outcome.CANNED_REPLY
    assert high["n-greet"].outcome is score_threshold.Outcome.BELOW_MINIMUM_MATCH_THRESHOLD
    # The shipped table's own number (0.80) is what the no-substitution case gives,
    # and substituting that same number reproduces it.
    assert shipped["n-greet"].outcome is score_threshold.Outcome.BELOW_MINIMUM_MATCH_THRESHOLD
    assert own["n-greet"].outcome is shipped["n-greet"].outcome


# --- precision: a post of the wrong Intent is wrong, never right ---------------


def test_a_wrong_intent_post_counts_against_precision_and_never_as_right(fixtures):
    """A gold-replyable Comment answered by a *different* Intent is a precision miss.

    `right` and `wrong_intent` both feed `posted`, so their union cannot tell the
    two apart -- only asserting which bucket a wrong-Intent post lands in does.
    """
    labelled, rows, _, decisions = fixtures
    table = score_threshold.load_reply_table()
    greet, join = rows[0], rows[3]  # gold GREETING (replyable), gold JOIN_ENQUIRY (gate)
    wrong = [
        # gold GREETING answered with a DOA_BLESSING entry at high confidence.
        _decision("n-greet", greet["norm"], "choice", confidences={"tt-doa-001": 0.95}),
        # a post against an Escalation gate, which must never enter precision.
        _decision("n-join", join["norm"], "choice", confidences={"tt-donate-001": 0.95}),
    ]
    rows = [greet, join]
    results = score_threshold.replay_all(rows, wrong, table)
    kind_by_nid = {record["nid"]: record["kind"] for record in wrong}
    weights = {row["nid"]: row["rows"] for row in rows}
    figures = score_threshold.bucket_figures(
        score_threshold._scored(rows, results, kind_by_nid),
        weights,
        score_threshold.replyable_intents(table),
    )
    assert figures["right"] == []
    assert figures["wrong_intent"] == ["n-greet"]
    assert figures["precision"] == 0.0
    assert figures["precision_rows"] == 0.0
    assert figures["covered"] == ["n-greet"]
    # The gate exclusion still holds: the JOIN_ENQUIRY post is a gate, not precision.
    assert figures["gate"] == ["n-join"]
    assert "n-join" not in figures["right"] + figures["wrong_intent"]

    # The opposite direction: a correct post is precision 1.0 with nothing wrong.
    correct = [
        _decision("n-greet", greet["norm"], "choice", confidences={"tt-greet-001": 0.95})
    ]
    results2 = score_threshold.replay_all([greet], correct, table)
    kind2 = {record["nid"]: record["kind"] for record in correct}
    figures2 = score_threshold.bucket_figures(
        score_threshold._scored([greet], results2, kind2),
        {greet["nid"]: greet["rows"]},
        score_threshold.replyable_intents(table),
    )
    assert figures2["right"] == ["n-greet"]
    assert figures2["wrong_intent"] == []
    assert figures2["precision"] == 1.0


# --- bar 3: an `uncertain` record is a refusal that replays, not "no record" ----


def test_an_uncertain_record_is_a_refusal_that_replays(capsys, tmp_path):
    """An `uncertain` record replays to `UNCERTAIN`, is counted, and is not incomplete.

    Dropping `UNCERTAIN` from `REPLAYABLE` turns a recorded refusal into a missing
    decision -- which would surface as an incomplete run and drop the Comment from
    the confidence distribution's "no confidences" bucket.
    """
    table = score_threshold.load_reply_table()
    row = _row("n-unsure", "komen tidak pasti langsung", "DOA_BLESSING")
    record = _decision("n-unsure", row["norm"], "uncertain", uncertain=True)
    labelled = _write_jsonl(tmp_path / "labelled.jsonl", [row])
    decisions = _write_jsonl(tmp_path / "decisions.jsonl", [record])

    results = score_threshold.replay_all([row], [record], table)
    assert results["n-unsure"].outcome is score_threshold.Outcome.UNCERTAIN

    _, out = _run(capsys, labelled, decisions)
    # A recorded refusal is a complete decision, not a Comment never asked about.
    assert "labelled Comments with no recorded decision (incomplete run): 0" in out
    assert "INCOMPLETE" not in out
    # It is counted in the distribution's no-confidences bucket.
    assert "no confidences (declined/uncertain)" in out


# --- D14: the pipeline routes `text`; a stale stored `norm` cannot change it ----


def test_replay_routes_the_text_not_a_stale_norm(fixtures):
    """D14: `replay_all` normalizes `text`, so a stale stored `norm` is inert.

    The real corpus has Comments where the stored `norm` (from an older normalizer)
    differs from `normalize(text)`. A replay that routed the stored `norm` would ask
    the Router about a different string and miss the recorded decision.
    """
    labelled, rows, _, decisions = fixtures
    table = score_threshold.load_reply_table()
    stale = _row("n-stale", "komen doa yang lama", "DOA_BLESSING")
    stale["norm"] = "norm lama yang berbeza"  # deliberately stale
    assert stale["norm"] != score_threshold.normalize(stale["text"])
    assert score_threshold.normalize(stale["norm"]) != score_threshold.normalize(stale["text"])
    # The decision is keyed by normalize(text) -- the pipeline's unit, not the norm.
    record = _decision(
        "n-stale",
        score_threshold.normalize(stale["text"]),
        "choice",
        confidences={"tt-doa-001": 0.9},
    )

    results = score_threshold.replay_all([stale], [record], table)
    assert results["n-stale"] is not None
    assert results["n-stale"].outcome is score_threshold.Outcome.CANNED_REPLY
