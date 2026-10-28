"""Score the Router's confidences against the hand-labelled set.

    python3 tools/score_threshold.py --stub          # prove the path, synthetic
    python3 tools/score_threshold.py                 # replay the recorded decisions
    python3 tools/score_threshold.py --decisions <file> --labelled <file>

Reads `data/candidates/random.labelled.jsonl` (the labelled set) and a decisions
file recorded by `tools/run_router_sweep.py`, and replays the recorded
confidences through `agent.matching.Matcher` at every threshold on the axis.

The scorer decides nothing. Every figure comes out of `Matcher`: a replay client
returns the recorded `Decisions` for a normalized Comment, and the Outcomes that
come back are counted. A point on the curve *is* the pipeline at that threshold --
for each entry, `dataclasses.replace(entry, minimum_match_threshold=t)` -- not a
model of it. Re-implementing eligibility, the argmax or the conflict rule here
would agree with the pipeline until the day it did not, and then report a curve
for a program nobody runs (D1).

Only the **random** set is scored. The boundary set is enriched -- it is where the
Intents collide, not how often they occur -- so a precision figure computed on it
would be a figure about the boundary families, not about the corpus.

Three numbers per threshold, and the third is the one that matters most:

  * **coverage** -- of the Comments that should get a Canned reply, how many did.
  * **precision** -- of the Replies posted to those Comments, how many were right.
  * **false replies on silence** -- Replies posted to a Comment whose correct
    handling is no Canned reply at all: NO_REPLY (a bare formula, an emoji, a
    drive-by support tag -- ADR 0018) or OUT_OF_SCOPE (a Reply was warranted and
    no entry fits; it Escalates). This is the worst error available: it publishes
    a non-sequitur in public, to someone who was not talking to us, or answers a
    bereavement with a blessing. Reported separately from precision because
    averaging it in hides exactly the failure the threshold exists to prevent.

Per ADR 0018, **OUT_OF_SCOPE is not a Comment that should get a Reply.** Only the
entries that can actually be posted are counted as replyable; "should get a Canned
reply" is read from the loaded reply table -- a gold Intent is replyable exactly
when it carries at least one `status: "approved"` entry (D6) -- never from a
hard-coded list. `HELP_REQUEST` and `JOIN_ENQUIRY` are Escalation gates, not
replyable classes: a post against one is its own named count and is never folded
into precision.

`maintainer_note`: no threshold can be picked from this file alone. It reports the
curve; the rule that picks a point on it is ADR 0019 -- tiered by what a wrong
Reply costs, with a floor -- and the four bars there are what a Comment must clear.
This file measures the Router and threshold layer only: Bar 1 (`agent/no_reply.py`)
and Bar 4 run outside the sweep (ADR 0019), so "false replies on silence" here is
the propensity of this layer to post into silence, not a claim that production
would post, and must not be read as licence to move those bars.

`--stub` generates synthetic decisions from the gold labels with a deliberate
error rate, so the whole path -- file format, curve, report -- is exercised before
the Router exists. Its output is marked SYNTHETIC. Per `prove-the-path-you-havent-run`,
a mode switch is only a config change once the code behind it has actually run.
"""

from __future__ import annotations

import argparse
import collections
import json
import random
import sys
from dataclasses import replace
from pathlib import Path
from typing import Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agent.matching import Decisions, MatchResult, Matcher
from agent.no_reply import no_reply_reason
from agent.normalize import normalize
from agent.record import Outcome
from agent.reply_table import ReplyTable, ReplyTableEntry, load_reply_table

# Inputs resolve from the repository root, not the working directory (AC 6).
DEFAULT_LABELLED = REPO_ROOT / "data" / "candidates" / "random.labelled.jsonl"
DEFAULT_DECISIONS = REPO_ROOT / "data" / "candidates" / "router.decisions.jsonl"

THRESHOLDS = [round(0.05 * i, 2) for i in range(1, 20)]  # 0.05 .. 0.95
FLOOR = 0.50

# Comments a Canned reply must not be posted to, whichever way the Router reads
# them. Both belong to "false replies on silence" (AC 3, ADR 0019).
SILENCE = ("NO_REPLY", "OUT_OF_SCOPE")
# Escalation gates: an Intent that holds no postable text (ADR 0014, ADR 0016).
# This is the fallback taxonomy for callers that do not pass a derived set; the
# report derives the real one from the loaded table (`gate_intents`), so a future
# `status: "escalate"` Intent is scored as a gate rather than mistaken for an
# UNCERTAIN gold Comment.
GATES = ("HELP_REQUEST", "JOIN_ENQUIRY")

# The four kinds a recorded call can carry (D3), plus a Variant hit, which is not
# a Router call at all.
CHOICE, DECLINED, UNCERTAIN, FAILURE, VARIANT = (
    "choice",
    "declined",
    "uncertain",
    "failure",
    "variant",
)
REPLAYABLE = (CHOICE, DECLINED, UNCERTAIN)


class MissingDecision(KeyError):
    """The replay asked about a Comment the decisions file has no record for.

    Raised rather than answered with a guess: a missing decision is a partial
    run, and manufacturing silence for a Comment the Router was never asked
    about would turn an unfinished sweep into coverage misses (D12).
    """


def load_labelled(path: Path) -> list[dict]:
    return [json.loads(line) for line in Path(path).open(encoding="utf-8") if line.strip()]


def load_decisions(path: Path) -> list[dict]:
    return [json.loads(line) for line in Path(path).open(encoding="utf-8") if line.strip()]


class ReplayDecisions:
    """A `DecisionsClient` that returns the recorded decision for a Comment.

    It does not decide; it replays. A Comment with no record raises
    :class:`MissingDecision` so a partial run is never scored as silence.
    """

    def __init__(self, by_state: Mapping[str, dict]) -> None:
        self._by_state = dict(by_state)

    def decide(
        self, normalized_comment: str, options: Sequence[ReplyTableEntry]
    ) -> Decisions | None:
        record = self._by_state.get(normalized_comment)
        if record is None:
            raise MissingDecision(normalized_comment)
        kind = record["kind"]
        if kind == DECLINED:
            return None
        if kind == UNCERTAIN:
            return Decisions(confidences={}, uncertain=True)
        if kind == CHOICE:
            return Decisions(confidences=dict(record["confidences"]))
        raise MissingDecision(normalized_comment)


def _replay_index(records: Sequence[dict]) -> dict[str, dict]:
    """state -> the last record for it, so a retried call takes its final shape."""
    index: dict[str, dict] = {}
    for record in records:
        if record["kind"] in REPLAYABLE:
            index[record["state"]] = record
    return index


def replay_all(
    rows: Sequence[dict], records: Sequence[dict], table: ReplyTable
) -> dict[str, MatchResult | None]:
    """Replay every labelled Comment through `Matcher` at the table's own numbers.

    The candidate's own ``text`` goes through the pipeline, because Receive ->
    Normalize is the production path (D14); ``None`` marks a Comment with no
    recorded decision (partial run), never a silence.
    """
    matcher = Matcher(table, ReplayDecisions(_replay_index(records)))
    results: dict[str, MatchResult | None] = {}
    for row in rows:
        try:
            results[row["nid"]] = matcher.match_comment(row["text"])
        except MissingDecision:
            results[row["nid"]] = None
    return results


def replyable_intents(table: ReplyTable) -> frozenset[str]:
    """The Intents a Canned reply can actually be posted for (D6)."""
    return frozenset(entry.intent for entry in table.entries if entry.status == "approved")


def gate_intents(table: ReplyTable) -> frozenset[str]:
    """The Escalation gates: the Intents that hold no postable text (ADR 0014/0016).

    Read from the loaded table, never a hard-coded list: an Intent is a gate when
    it carries an entry with ``status: "escalate"``. Deriving it means a future
    ``escalate`` Intent is scored as a gate, not reported as a post against an
    UNCERTAIN gold Comment.
    """
    return frozenset(entry.intent for entry in table.entries if entry.status == "escalate")


def with_threshold(table: ReplyTable, threshold: float) -> ReplyTable:
    """Every entry at one threshold -- a point on the curve *is* the pipeline (D1)."""
    return ReplyTable(
        entries=tuple(
            replace(entry, minimum_match_threshold=threshold) for entry in table.entries
        )
    )


def _weight(weights: Mapping[str, int], nids: Sequence[str]) -> int:
    return sum(weights[nid] for nid in nids)


def _ratio(numerator: int, denominator: int) -> float:
    return (numerator / denominator) if denominator else float("nan")


def _fmt_ratio(value: float) -> str:
    return " n/a" if value != value else f"{value:.3f}"


def _scored(
    rows: Sequence[dict],
    results: Mapping[str, MatchResult | None],
    kind_by_nid: Mapping[str, str],
) -> list[tuple[dict, MatchResult]]:
    """The (row, MatchResult) pairs a threshold figure is computed over.

    Variant hits are excluded (D3): they are answered at confidence 1.0 by
    construction and say nothing about a threshold. A failure or a missing
    decision is excluded too -- it is reported as an incomplete run (D12/D13),
    never as silence.
    """
    scored: list[tuple[dict, MatchResult]] = []
    for row in rows:
        nid = row["nid"]
        if kind_by_nid.get(nid) in (VARIANT, FAILURE):
            continue
        result = results.get(nid)
        if result is None:
            continue
        scored.append((row, result))
    return scored


def bucket_figures(
    scored: Sequence[tuple[dict, MatchResult]],
    weights: Mapping[str, int],
    replyable: frozenset[str],
    gates: frozenset[str] = frozenset(GATES),
) -> dict:
    """The posted/coverage/precision/silence figures for one configuration."""
    right: list[str] = []
    wrong_intent: list[str] = []
    silence: list[str] = []
    silence_noreply: list[str] = []
    silence_tail: list[str] = []
    gate: list[str] = []
    uncertain_post: list[str] = []
    covered: list[str] = []
    replyable_pop: list[str] = []

    for row, result in scored:
        nid, gold = row["nid"], row["label"]
        if gold in replyable:
            replyable_pop.append(nid)
        if result.outcome is not Outcome.CANNED_REPLY:
            continue
        posted_intent = result.entry.intent if result.entry is not None else None
        if gold in replyable:
            covered.append(nid)
            if posted_intent == gold:
                right.append(nid)
            else:
                wrong_intent.append(nid)
        elif gold in SILENCE:
            silence.append(nid)
            (silence_noreply if gold == "NO_REPLY" else silence_tail).append(nid)
        elif gold in gates:
            gate.append(nid)
        else:  # gold UNCERTAIN
            uncertain_post.append(nid)

    intended = right + wrong_intent
    return {
        "replyable_pop": replyable_pop,
        "covered": covered,
        "right": right,
        "wrong_intent": wrong_intent,
        "posted": intended + silence + gate + uncertain_post,
        "precision": _ratio(len(right), len(intended)),
        "precision_rows": _ratio(_weight(weights, right), _weight(weights, intended)),
        "coverage": _ratio(len(covered), len(replyable_pop)),
        "coverage_rows": _ratio(
            _weight(weights, covered), _weight(weights, replyable_pop)
        ),
        "silence": silence,
        "silence_noreply": silence_noreply,
        "silence_tail": silence_tail,
        "gate": gate,
        "uncertain_post": uncertain_post,
    }


def outcome_figures(
    scored: Sequence[tuple[dict, MatchResult]]
) -> tuple[collections.Counter, dict[str, tuple[str, ...]]]:
    """Per-Outcome counts, and the Intents named by each conflict (D7)."""
    outcomes: collections.Counter = collections.Counter()
    conflicts: dict[str, tuple[str, ...]] = {}
    for row, result in scored:
        outcomes[result.outcome.name] += 1
        if result.outcome is Outcome.CONFLICTING_INTENTS:
            conflicts[row["nid"]] = tuple(
                part.strip()
                for part in result.detail.removeprefix("conflicting intents:").split(",")
                if part.strip()
            )
    return outcomes, conflicts


def stub_decisions(rows: Sequence[dict], table: ReplyTable, seed: int = 20261021) -> list[dict]:
    """Synthetic decisions from the gold labels, with a deliberate error rate.

    It exercises the whole path without a key or a network. Gold NO_REPLY and
    OUT_OF_SCOPE rows get a posting decision only sometimes, which is what makes
    "false replies on silence" a number worth reading; a real gold Tail also
    appears as a declined reading.
    """
    rng = random.Random(seed)
    by_intent: dict[str, list[str]] = collections.defaultdict(list)
    for entry in table.entries:
        if entry.status == "approved":
            by_intent[entry.intent].append(entry.reply_id)
    postable = [reply_id for ids in by_intent.values() for reply_id in ids]

    out: list[dict] = []
    for row in rows:
        gold = row["label"]
        state = normalize(row["text"])
        if gold in SILENCE:
            if rng.random() < 0.15:
                out.append(_stub_choice(row, state, rng.choice(postable),
                                        round(rng.uniform(0.30, 0.95), 3)))
            else:
                out.append(_stub_record(row, state, DECLINED, {}, False))
            continue
        if gold == "UNCERTAIN":
            out.append(_stub_record(row, state, UNCERTAIN, {}, True))
            continue
        if rng.random() < 0.80 and by_intent.get(gold):
            chosen = rng.choice(by_intent[gold])
            out.append(_stub_choice(row, state, chosen, round(rng.uniform(0.55, 0.99), 3)))
        else:
            others = [i for i in postable if i not in by_intent.get(gold, [])]
            out.append(_stub_choice(row, state, rng.choice(others or postable),
                                    round(rng.uniform(0.25, 0.70), 3)))
    return out


def _stub_record(row: dict, state: str, kind: str, confidences: dict, uncertain: bool) -> dict:
    return {
        "nid": row["nid"],
        "state": state,
        "kind": kind,
        "confidences": confidences,
        "uncertain": uncertain,
        "chosen": None,
        "probabilities": {},
        "failure": None,
        "outcome": None,
        "detail": "",
    }


def _stub_choice(row: dict, state: str, reply_id: str, confidence: float) -> dict:
    return _stub_record(row, state, CHOICE, {reply_id: confidence}, False)


def report(
    rows: Sequence[dict],
    records: Sequence[dict],
    table: ReplyTable,
    *,
    labelled_path: Path,
    decisions_path: Path,
    synthetic: bool,
) -> None:
    replyable = replyable_intents(table)
    gates = gate_intents(table)
    weights = {row["nid"]: row["rows"] for row in rows}
    label_by_nid = {row["nid"]: row["label"] for row in rows}
    label_text = {row["nid"]: row["text"] for row in rows}
    labelled_nids = {row["nid"] for row in rows}
    kind_by_nid = {record["nid"]: record["kind"] for record in records}
    by_nid = {record["nid"]: record for record in records}

    print(f"labelled:  {labelled_path}")
    print(f"decisions: {decisions_path}")
    if synthetic:
        print("\n*** SYNTHETIC DECISIONS -- these numbers describe the harness, "
              "not the Router ***")

    # --- D14: the labelling unit and the pipeline's unit are the same string ---
    mismatch = [row["nid"] for row in rows if normalize(row["text"]) != row["norm"]]
    print(f"\nnormalize(text) != norm (D14): {len(mismatch)} distinct Comments"
          " -- if non-zero the labelled unit and the pipeline's unit differ")

    # --- D12: a partial or stale run is visible, never silently scored ---
    decision_nids = {record["nid"] for record in records}
    unknown = sorted(decision_nids - labelled_nids)
    unlabelled = [row["nid"] for row in rows if not row.get("label")]
    variant_nids = [nid for nid, kind in kind_by_nid.items() if kind == VARIANT]
    failure_nids = [nid for nid, kind in kind_by_nid.items() if kind == FAILURE]
    print(f"labelled Comments: {len(rows)}   corpus rows: {sum(weights.values())}")
    print(f"decisions naming a Comment not in the labelled set (stale): {len(unknown)}")
    # A Comment recorded twice collapses to its last line in the replay index and in
    # `by_nid`; report the count so a doubled run is visible rather than silent.
    duplicate_nids = [
        nid for nid, count in collections.Counter(r["nid"] for r in records).items()
        if count > 1
    ]
    print(f"decisions carrying a duplicate nid (last wins): {len(duplicate_nids)}")
    print(f"labelled rows carrying no label: {len(unlabelled)}")

    results = replay_all(rows, records, table)
    scored = _scored(rows, results, kind_by_nid)
    scored_nids = {row["nid"] for row, _ in scored}
    missing = [
        row["nid"]
        for row in rows
        if row["nid"] not in scored_nids
        and kind_by_nid.get(row["nid"]) not in (VARIANT, FAILURE)
    ]
    print(f"failures (a failure is not a decision): {len(failure_nids)}")
    print(f"labelled Comments with no recorded decision (incomplete run): {len(missing)}")
    # The recorded Outcome is a snapshot at the table's thresholds when the run was
    # made. If a tier number has since moved, the file predates the revision -- a
    # stale run, not a scorer bug (the confidences are threshold-independent).
    stale_outcome = [
        row["nid"]
        for row, result in scored
        if by_nid.get(row["nid"], {}).get("outcome")
        not in (None, result.outcome.name)
    ]
    print(f"decisions recorded at an earlier table (recorded outcome != replayed): "
          f"{len(stale_outcome)}")
    if missing or failure_nids or unknown:
        print("  -> the run is INCOMPLETE or STALE; the figures below cover only"
              " the Comments with a recorded decision and must not be read as the"
              " whole set")

    # --- D3: a Variant hit is not evidence about any threshold ---
    variant_rows = [row for row in rows if kind_by_nid.get(row["nid"]) == VARIANT]
    print(f"\nVariant hits (no Router call, reported separately, not in coverage): "
          f"{len(variant_rows)} distinct, "
          f"{_weight(weights, [r['nid'] for r in variant_rows])} rows")
    vlabels = collections.Counter(row["label"] for row in variant_rows)
    if vlabels:
        print("  by gold label: " + ", ".join(f"{k} {v}" for k, v in vlabels.most_common()))
    variant_silence = [row for row in variant_rows if row["label"] in SILENCE]
    if variant_silence:
        print(f"  Variant hits posting into silence: {len(variant_silence)} distinct, "
              f"{_weight(weights, [r['nid'] for r in variant_silence])} rows"
              " (a Variant error, not a threshold error)")

    # --- the shipped configuration, each entry at its own number ---
    figures = bucket_figures(scored, weights, replyable, gates)
    print("\n=== shipped configuration (each entry at its own minimum_match_threshold) ===")
    print(f"should get a Canned reply: {len(figures['replyable_pop'])} distinct, "
          f"{_weight(weights, figures['replyable_pop'])} rows")
    print(f"coverage:  {len(figures['covered'])}/{len(figures['replyable_pop'])} "
          f"({_fmt_ratio(figures['coverage'])}) distinct; "
          f"{_weight(weights, figures['covered'])}/{_weight(weights, figures['replyable_pop'])} "
          f"({_fmt_ratio(figures['coverage_rows'])}) rows")
    print(f"precision: {len(figures['right'])}/"
          f"{len(figures['right']) + len(figures['wrong_intent'])} "
          f"({_fmt_ratio(figures['precision'])}) distinct; "
          f"{_weight(weights, figures['right'])}/"
          f"{_weight(weights, figures['right']) + _weight(weights, figures['wrong_intent'])} "
          f"({_fmt_ratio(figures['precision_rows'])}) rows")
    print(f"false replies on silence (NO_REPLY or OUT_OF_SCOPE): "
          f"{len(figures['silence'])} distinct, {_weight(weights, figures['silence'])} rows")
    print(f"  NO_REPLY:     {len(figures['silence_noreply'])} distinct, "
          f"{_weight(weights, figures['silence_noreply'])} rows")
    print(f"  OUT_OF_SCOPE: {len(figures['silence_tail'])} distinct, "
          f"{_weight(weights, figures['silence_tail'])} rows")
    print(f"wrong posts against an Escalation gate (HELP_REQUEST/JOIN_ENQUIRY): "
          f"{len(figures['gate'])} distinct, {_weight(weights, figures['gate'])} rows"
          " -- never folded into precision")
    print(f"posts to an UNCERTAIN gold Comment: {len(figures['uncertain_post'])} distinct, "
          f"{_weight(weights, figures['uncertain_post'])} rows")

    # --- Bar 1 decomposition: what of the false-on-silence Bar 1 already catches ---
    # Bar 1 (`agent/no_reply.py`) runs outside the sweep, before the Router (ADR
    # 0019). The scorer cannot decide it, but it can report how much of the
    # false-on-silence the structural test would already have refused -- so the
    # residue the Router+threshold layer is actually responsible for is visible.
    refused_by_bar_one = [
        nid for nid in figures["silence"] if no_reply_reason(label_text[nid]) is not None
    ]
    reachable = [
        nid for nid in figures["silence"] if no_reply_reason(label_text[nid]) is None
    ]
    print("\n=== Bar 1 decomposition (agent/no_reply.py, outside the sweep -- ADR 0019) ===")
    print(f"false replies on silence at the shipped thresholds: {len(figures['silence'])} "
          f"distinct, {_weight(weights, figures['silence'])} rows")
    print(f"  already refused by no_reply_reason (Bar 1): {len(refused_by_bar_one)} distinct, "
          f"{_weight(weights, refused_by_bar_one)} rows")
    print(f"  reachable by the Router + threshold layer: {len(reachable)} distinct, "
          f"{_weight(weights, reachable)} rows")
    if reachable:
        reach_labels = collections.Counter(label_by_nid[nid] for nid in reachable)
        print("  reachable by gold label: "
              + ", ".join(f"{k} {v}" for k, v in reach_labels.most_common()))

    # --- D7: refusal accounting is per-Outcome and disjoint ---
    outcomes, conflicts = outcome_figures(scored)
    print("\nper-Outcome (each Comment lands in exactly one; the bars and the Tail"
          " are disjoint):")
    for name in sorted(outcomes, key=lambda n: -outcomes[n]):
        nids = [row["nid"] for row, result in scored if result.outcome.name == name]
        print(f"  {name:32s} {outcomes[name]:4d} distinct, {_weight(weights, nids):4d} rows")
    if conflicts:
        pair_counts = collections.Counter(
            tuple(sorted(intents)) for intents in conflicts.values()
        )
        print("  conflicts by Intent pair (a compatible pair both above threshold"
              " still Escalates):")
        for pair, count in pair_counts.most_common():
            print(f"    {' + '.join(pair) or '(unknown)'}: {count}")

    # --- D8/D9: the shipped configuration per tier, and the thin tier ---
    print("\n=== per tier (membership read from the loaded table, each entry's own number) ===")
    print(f"{'threshold':>9} {'intents':<28} {'gold':>5} {'rows':>5} "
          f"{'covered':>7} {'coverage':>8} {'wrong':>5}  flag")
    tiers: dict[float, set[str]] = collections.defaultdict(set)
    for entry in table.entries:
        tiers[entry.minimum_match_threshold].add(entry.intent)
    thin: list[tuple[float, int]] = []
    for threshold in sorted(tiers, reverse=True):
        intents = tiers[threshold]
        pop = [row for row, _ in scored if row["label"] in intents]
        covered = [
            row for row, result in scored
            if row["label"] in intents and result.outcome is Outcome.CANNED_REPLY
        ]
        wrong = [
            row for row, result in scored
            if row["label"] in intents
            and result.outcome is Outcome.CANNED_REPLY
            and (result.entry is None or result.entry.intent != row["label"])
        ]
        cov = _ratio(len(covered), len(pop))
        flag = ""
        if len(pop) < 10:
            flag = "THIN (<10 distinct gold Comments)"
            thin.append((threshold, len(pop)))
        print(f"{threshold:9.2f} {','.join(sorted(intents)):<28} "
              f"{len(pop):5d} {_weight(weights, [r['nid'] for r in pop]):5d} "
              f"{len(covered):7d} {_fmt_ratio(cov):>8} {len(wrong):5d}  {flag}")
    if thin:
        for threshold, count in thin:
            print(f"  -> the tier at {threshold:.2f} is too thin to be worth configuring:"
                  f" {count} distinct gold Comments (single digits cannot carry a rate)")
    else:
        print("  -> no tier is thin on the scored set")

    # --- the confidence distribution: is the curve a step function? ---
    print("\n=== confidence distribution (max confidence among the entries _route sees) ===")
    bins = [(0.0, 0.2), (0.2, 0.5), (0.5, 0.65), (0.65, 0.9), (0.9, 1.01)]
    hist = collections.Counter()
    hist_rows = collections.Counter()
    for row, result in scored:
        record = by_nid.get(row["nid"])
        confidences = record.get("confidences") if record else None
        if not confidences:
            hist["no confidences (declined/uncertain)"] += 1
            hist_rows["no confidences (declined/uncertain)"] += weights[row["nid"]]
            continue
        top = max(confidences.values())
        label = next(f"[{low:.2f},{high:.2f})" for low, high in bins if low <= top < high)
        hist[label] += 1
        hist_rows[label] += weights[row["nid"]]
    for label in [f"[{low:.2f},{high:.2f})" for low, high in bins] + [
        "no confidences (declined/uncertain)"
    ]:
        if hist[label]:
            print(f"  {label:36s} {hist[label]:4d} distinct, {hist_rows[label]:4d} rows")

    # --- the global curve: the shape of the trade-off ---
    print("\n=== global curve (every entry at one threshold) ===")
    print("below 0.50 is a floor violation rather than a configuration (ADR 0019)")
    print("each figure is given twice: distinct (rows)")
    print(f"{'thresh':>6} {'posted':>12} {'prec':>16} {'cover':>16} "
          f"{'false-silence':>16} {'gate':>10} {'missed':>12}")
    for threshold in THRESHOLDS:
        curve_results = replay_all(rows, records, with_threshold(table, threshold))
        curve_scored = _scored(rows, curve_results, kind_by_nid)
        fig = bucket_figures(curve_scored, weights, replyable, gates)
        covered = set(fig["covered"])
        missed = [
            row for row, _ in curve_scored
            if row["label"] in replyable and row["nid"] not in covered
        ]
        note = "  <- below floor" if threshold < FLOOR else ""
        print(f"{threshold:6.2f} {len(fig['posted']):5d} "
              f"({_weight(weights, fig['posted']):4d}r) "
              f"{_fmt_ratio(fig['precision']):>7} "
              f"({_fmt_ratio(fig['precision_rows']):>6}r) "
              f"{_fmt_ratio(fig['coverage']):>7} "
              f"({_fmt_ratio(fig['coverage_rows']):>6}r) "
              f"{len(fig['silence']):5d} ({_weight(weights, fig['silence']):>3d}r) "
              f"{len(fig['gate']):4d} ({_weight(weights, fig['gate']):>3d}r) "
              f"{len(missed):5d} "
              f"({_weight(weights, [row['nid'] for row in missed]):>4d}r){note}")

    print("\nThis measures the Router and threshold layer only. Bar 1 (agent/no_reply.py)"
          " and Bar 4 run outside the sweep (ADR 0019), so 'false replies on silence'"
          " here is this layer's propensity to post into silence, not a claim that"
          " production would post, and must not be read as licence to move those bars.")


def _missing_input(path: Path) -> int:
    """Report a missing input as a missing input -- and nothing else (AC 6)."""
    print(f"missing input: {Path(path).resolve()}", file=sys.stderr)
    return 2


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--labelled", default=str(DEFAULT_LABELLED))
    parser.add_argument("--decisions", default=str(DEFAULT_DECISIONS))
    parser.add_argument("--stub", action="store_true")
    args = parser.parse_args(argv)

    labelled_path = Path(args.labelled)
    decisions_path = Path(args.decisions)
    if not labelled_path.exists():
        return _missing_input(labelled_path)
    if not args.stub and not decisions_path.exists():
        return _missing_input(decisions_path)

    rows = load_labelled(labelled_path)
    table = load_reply_table()
    if args.stub:
        records = stub_decisions(rows, table)
    else:
        records = load_decisions(decisions_path)
    report(
        rows,
        records,
        table,
        labelled_path=labelled_path.resolve(),
        decisions_path=decisions_path.resolve(),
        synthetic=args.stub,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
