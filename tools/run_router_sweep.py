"""Drive the real Router over the labelled set and record what it returned.

    python3 tools/run_router_sweep.py                    # ~401 calls, tens of minutes
    python3 tools/run_router_sweep.py --labelled <file> --decisions <file> --journal <file>

This is the network half of the measurement (D2). It builds the real
:class:`agent.router.OpenRouterDecisions` -- the key comes from the environment
and is never written anywhere -- wraps it in a recorder, drives
``Matcher.match_comment(candidate["text"])`` over the labelled set, and appends
one decision line per Comment to the decisions file.

The scorer (`tools/score_threshold.py`) reads that file and replays. A figure in
ADR 0019 that cannot be re-checked without a key and a network is not evidence
anyone can audit, so the two halves are separate programs.

**What is recorded, per Comment (D3):** the labelled ``nid``, the normalized
Comment handed to the Router, which of ``choice``/``declined``/``uncertain``/
``failure`` the call produced, the confidences ``_route`` will see, the raw
``chosen`` value including the sentinel, the raw ``probabilities``, whether the
Comment was answered by a declared Variant with no Router call at all, and the
``Matcher``'s own ``Outcome`` and ``detail`` at the shipped thresholds. The
sentinel is never re-derived: the raw ``chosen`` is recorded for legibility only.

**A failure is not a decision (D13).** A ``RouterUnavailable`` is recorded in the
journal by the client -- **one line per attempt, and the retry attempts the
byte-identical request**, so a failure that exhausts ``attempts=3`` writes three
lines, one per try. (The brief's "exactly one line" is read as one line per
attempt: each failed call is a real call that the journal must keep, and collapsing
them would hide the retry from the record.) After the bounded retry the run aborts
loudly, naming the Comment by its labelled ``nid`` and its index in the sweep. It is
written to the decisions file as ``kind: "failure"`` and **never** as a decline or
a Tail: outcomes are insert-only (ADR 0008) and the Tail is a class the sweep
counts, so a failure resolved to the Tail would corrupt the curve permanently.

**Every line is appended as it is made (D12).** A crash leaves a readable partial
file, and the scorer reports the run as incomplete rather than scoring the
Comments the Router was never asked about as if it had gone quiet on them.

Nothing per-Comment is committed (D16): the labelled set, the decisions file and
the journal all live under the gitignored ``data/`` and only aggregate figures
reach the committed docs.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agent.matching import Decisions, Matcher
from agent.normalize import normalize
from agent.reply_table import ReplyTable, ReplyTableEntry, load_reply_table
from agent.router import (
    API_KEY_ENV,
    DecisionJournal,
    OpenRouterDecisions,
    RouterUnavailable,
)

# Inputs and outputs resolve from the repository root, not the working directory
# (AC 6). All three are gitignored (D16).
DEFAULT_LABELLED = REPO_ROOT / "data" / "candidates" / "random.labelled.jsonl"
DEFAULT_DECISIONS = REPO_ROOT / "data" / "candidates" / "router.decisions.jsonl"
DEFAULT_JOURNAL = REPO_ROOT / "data" / "candidates" / "router.journal.jsonl"

CHOICE, DECLINED, UNCERTAIN, FAILURE, VARIANT = (
    "choice",
    "declined",
    "uncertain",
    "failure",
    "variant",
)


class SweepAborted(RouterUnavailable):
    """A failure that stopped the sweep, carrying the Comment it stopped on (D13).

    A bare ``RouterUnavailable`` names the cause but not *which* Comment produced
    it, so a half-run is not diagnosable. This carries the labelled ``nid`` and the
    index/count, and is raised in place of the cause so the abort can name the
    Comment. It is a ``RouterUnavailable`` subclass, so a caller that only knows the
    base class still sees the failure.
    """

    def __init__(self, cause: RouterUnavailable, *, nid: str, position: int, total: int) -> None:
        super().__init__(str(cause))
        self.nid = nid
        self.position = position
        self.total = total


def load_labelled(path: Path) -> list[dict]:
    return [json.loads(line) for line in Path(path).open(encoding="utf-8") if line.strip()]


class RecordingDecisions:
    """A `DecisionsClient` that records what the wrapped client returned (D3).

    It records the four kinds a call can produce, the confidences ``_route`` will
    see, and -- when a journal path is supplied -- the raw ``chosen`` and
    ``probabilities`` the client wrote, read back rather than re-derived. A
    ``RouterUnavailable`` is retried a bounded number of times on the
    byte-identical request (D13), then recorded as a failure and re-raised.
    """

    def __init__(
        self,
        inner,
        *,
        journal_path: Path | None = None,
        attempts: int = 3,
    ) -> None:
        self.inner = inner
        self.journal_path = Path(journal_path) if journal_path else None
        self.attempts = max(1, attempts)
        self.calls: dict[str, dict] = {}

    def decide(
        self, normalized_comment: str, options: Sequence[ReplyTableEntry]
    ) -> Decisions | None:
        result: Decisions | None = None
        for attempt in range(self.attempts):
            try:
                result = self.inner.decide(normalized_comment, options)
                break
            except RouterUnavailable:
                if attempt == self.attempts - 1:
                    self.calls[normalized_comment] = {
                        "kind": FAILURE,
                        "confidences": {},
                        "uncertain": False,
                        "raw": None,
                    }
                    raise

        if result is None:
            kind, confidences, uncertain = DECLINED, {}, False
        elif result.uncertain:
            kind, confidences, uncertain = UNCERTAIN, {}, True
        else:
            kind, confidences, uncertain = CHOICE, dict(result.confidences), False
        self.calls[normalized_comment] = {
            "kind": kind,
            "confidences": confidences,
            "uncertain": uncertain,
            "raw": self._raw(),
        }
        return result

    def _raw(self) -> dict | None:
        """The last journal line the wrapped client wrote -- for legibility only."""
        if self.journal_path is None or not self.journal_path.exists():
            return None
        last: dict | None = None
        for line in self.journal_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                last = json.loads(line)
        return last


class DecisionWriter:
    """Append one decision line per Comment, the way `DecisionJournal` writes (D12)."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def append(self, entry: Mapping) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(
            self.path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600
        )
        try:
            os.chmod(self.path, 0o600)
            with os.fdopen(descriptor, "a", encoding="utf-8") as stream:
                descriptor = -1
                stream.write(json.dumps(entry, ensure_ascii=False) + "\n")
        finally:
            if descriptor >= 0:
                os.close(descriptor)


def _record(
    *,
    nid: str,
    state: str,
    kind: str,
    call: Mapping | None,
    result,
    failure: str | None,
) -> dict:
    raw = (call or {}).get("raw") or {}
    return {
        "nid": nid,
        "state": state,
        "kind": kind,
        "confidences": dict((call or {}).get("confidences") or {}),
        "uncertain": bool((call or {}).get("uncertain")),
        "chosen": raw.get("chosen"),
        "probabilities": raw.get("probabilities") or {},
        "failure": failure,
        "outcome": result.outcome.name if result is not None else None,
        "detail": result.detail if result is not None else "",
    }


def run_sweep(
    rows: Sequence[dict],
    table: ReplyTable,
    client,
    *,
    decisions_path: str | Path,
    journal_path: str | Path | None = None,
    attempts: int = 3,
) -> int:
    """Drive ``Matcher`` over the labelled set and append a decision per Comment.

    Returns the number of Comments recorded. A ``RouterUnavailable`` is written
    as a failure line and re-raised so the caller can abort loudly (D13).
    """
    recorder = RecordingDecisions(client, journal_path=journal_path, attempts=attempts)
    matcher = Matcher(table, recorder)
    writer = DecisionWriter(decisions_path)
    recorded = 0
    total = len(rows)
    for position, row in enumerate(rows, start=1):
        nid = row["nid"]
        try:
            result = matcher.match_comment(row["text"])
        except RouterUnavailable as exc:
            state = normalize(row["text"])
            writer.append(
                _record(
                    nid=nid,
                    state=state,
                    kind=FAILURE,
                    call={"kind": FAILURE, "confidences": {}, "uncertain": False, "raw": None},
                    result=None,
                    failure=str(exc),
                )
            )
            # Name the Comment, loudly, so a half-run is diagnosable (D13).
            raise SweepAborted(exc, nid=nid, position=position, total=total) from exc
        state = result.normalized_comment
        call = recorder.calls.get(state)
        kind = call["kind"] if call else VARIANT
        writer.append(
            _record(nid=nid, state=state, kind=kind, call=call, result=result, failure=None)
        )
        recorded += 1
    return recorded


def _missing_input(path: Path) -> int:
    """Report a missing input as a missing input -- and nothing else (AC 6)."""
    print(f"missing input: {Path(path).resolve()}", file=sys.stderr)
    return 2


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--labelled", default=str(DEFAULT_LABELLED))
    parser.add_argument("--decisions", default=str(DEFAULT_DECISIONS))
    parser.add_argument("--journal", default=str(DEFAULT_JOURNAL))
    parser.add_argument("--model", default=None)
    parser.add_argument("--attempts", type=int, default=3)
    args = parser.parse_args(argv)

    labelled_path = Path(args.labelled)
    if not labelled_path.exists():
        return _missing_input(labelled_path)
    if not os.environ.get(API_KEY_ENV):
        print(f"{API_KEY_ENV} is not set; the Router cannot be constructed without a key",
              file=sys.stderr)
        return 2

    rows = load_labelled(labelled_path)
    table = load_reply_table()
    journal = DecisionJournal(args.journal)
    overrides = {"model": args.model} if args.model else {}
    client = OpenRouterDecisions(journal=journal, **overrides)

    print(f"driving {len(rows)} labelled Comments through {client.base_url} "
          f"model={client.model}")
    try:
        recorded = run_sweep(
            rows,
            table,
            client,
            decisions_path=args.decisions,
            journal_path=args.journal,
            attempts=args.attempts,
        )
    except RouterUnavailable as exc:
        # Name the Comment, loudly, and abort -- never resolve it to a Tail (D13).
        if isinstance(exc, SweepAborted):
            print(f"\nthe Router failed and the run aborted at Comment {exc.position}/{exc.total} "
                  f"(nid {exc.nid}): {exc}", file=sys.stderr)
        else:
            print(f"\nthe Router failed and the run aborted: {exc}", file=sys.stderr)
        return 1
    print(f"recorded {recorded} decisions -> {Path(args.decisions).resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
