"""Score the Router's confidences against the hand-labelled set.

    python3 tools/score_threshold.py --stub          # prove the path, synthetic
    python3 tools/score_threshold.py <predictions>   # real Router output

Reads `data/candidates/random.labelled.jsonl` (the labelled set) and a predictions
file of `{nid, intent, confidence}` lines, and sweeps `minimum_match_threshold`.

Only the **random** set is scored. The boundary set is enriched -- it is where the
Intents collide, not how often they occur -- so a precision figure computed on it
would be a figure about the boundary families, not about the corpus.

Three numbers per threshold, and the third is the one that matters most:

  * **coverage** -- of the Comments that should get a Canned reply, how many did.
  * **precision** -- of the Replies that would be posted, how many were right.
  * **false replies on silence** -- Replies posted to a Comment whose correct
    handling is no Canned reply at all: NO_REPLY (a bare formula, an emoji, a
    drive-by support tag -- ADR 0018) or OUT_OF_SCOPE (a Reply was warranted and
    no entry fits; it Escalates). This is the worst error available: it publishes
    a non-sequitur in public, to someone who was not talking to us, or answers a
    bereavement with a blessing. Reported separately from precision because
    averaging it in hides exactly the failure the threshold exists to prevent.

Per ADR 0018, **OUT_OF_SCOPE is not a Comment that should get a Reply.** Only the
entries that can actually be posted are counted as replyable; a prediction naming
OUT_OF_SCOPE is the Router saying "gap", not a selection to post. Counting it as a
coverage miss and a precision hit at once would measure nothing.

`maintainer_note`: no threshold can be picked from this file alone. It reports the
curve; the rule that picks a point on it is ADR 0019 -- tiered by what a wrong
Reply costs, with a floor -- and the four bars there are what a Comment must clear.
The numbers in that ADR are defaults until this file runs against Jev's real
confidences rather than the stub's.

`--stub` generates synthetic predictions from the gold labels with a deliberate
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
from pathlib import Path

from apply_labels import INTENTS

CANDIDATES = Path("data/candidates")
LABELLED = CANDIDATES / "random.labelled.jsonl"
THRESHOLDS = [round(0.05 * i, 2) for i in range(1, 20)]  # 0.05 .. 0.95

# The Intents that hold postable text. OUT_OF_SCOPE is an Intent in the labelling
# vocabulary but has no Canned reply and never will (ADR 0018) -- it is the Tail.
POSTABLE = [i for i in INTENTS if i != "OUT_OF_SCOPE"]
# Comments a Canned reply must not be posted to, whichever way the Router reads them.
SILENT = ("NO_REPLY", "OUT_OF_SCOPE")


def load_labelled() -> list[dict]:
    return [json.loads(l) for l in LABELLED.open(encoding="utf-8") if l.strip()]


def stub_predictions(rows: list[dict], seed: int = 20261021) -> list[dict]:
    """Synthetic Router output: right 80% of the time, wrong 20%, with overlap.

    Gold NO_REPLY and OUT_OF_SCOPE rows get a posting prediction only sometimes,
    which is what makes 'false replies on silence' a number worth reading.
    """
    rng = random.Random(seed)
    out: list[dict] = []
    for r in rows:
        gold = r["label"]
        if gold in SILENT:
            if rng.random() < 0.15:  # the Router should mostly stay quiet here
                out.append({"nid": r["nid"], "intent": rng.choice(POSTABLE),
                            "confidence": round(rng.uniform(0.30, 0.75), 3)})
            continue
        if gold == "UNCERTAIN":
            continue
        if rng.random() < 0.80:
            out.append({"nid": r["nid"], "intent": gold,
                        "confidence": round(rng.uniform(0.55, 0.99), 3)})
        else:
            out.append({"nid": r["nid"], "intent": rng.choice(
                [i for i in POSTABLE if i != gold]),
                "confidence": round(rng.uniform(0.25, 0.70), 3)})
    return out


def sweep(rows: list[dict], preds: list[dict], threshold: float) -> dict:
    gold = {r["nid"]: r["label"] for r in rows}
    weights = {r["nid"]: r["rows"] for r in rows}

    # Only a prediction naming a postable entry, above threshold, is a selection to
    # post. A prediction naming OUT_OF_SCOPE is the Router declining.
    best: dict[str, dict] = {}
    for p in preds:
        if p["confidence"] < threshold or p["intent"] not in POSTABLE:
            continue
        cur = best.get(p["nid"])
        if cur is None or p["confidence"] > cur["confidence"]:
            best[p["nid"]] = p

    should_reply = [n for n, g in gold.items() if g in POSTABLE]

    def w(ns: list[str]) -> int:
        return sum(weights[n] for n in ns)

    intended = [n for n in best if gold[n] in POSTABLE]
    right = [n for n in intended if best[n]["intent"] == gold[n]]
    false_on_silence = [n for n in best if gold[n] in SILENT]
    posted = intended + false_on_silence
    missed = [n for n in should_reply if n not in best]

    return {
        "threshold": threshold,
        "posted": len(posted), "posted_rows": w(posted),
        "right": len(right), "right_rows": w(right),
        "precision": (len(right) / len(posted)) if posted else float("nan"),
        "coverage": (len(intended) / len(should_reply)) if should_reply else float("nan"),
        "false_on_silence": len(false_on_silence),
        "false_on_silence_rows": w(false_on_silence),
        "missed": len(missed), "missed_rows": w(missed),
    }


def report(rows: list[dict], preds: list[dict], synthetic: bool) -> None:
    gold = collections.Counter(r["label"] for r in rows if r["label"] in POSTABLE)
    print("gold (distinct Comments that should get a Canned reply): "
          + ", ".join(f"{k} {v}" for k, v in gold.most_common()))
    print(f"gold NO_REPLY: {sum(1 for r in rows if r['label'] == 'NO_REPLY')}   "
          f"gold OUT_OF_SCOPE (Tail, Escalates): "
          f"{sum(1 for r in rows if r['label'] == 'OUT_OF_SCOPE')}   "
          f"excluded UNCERTAIN: {sum(1 for r in rows if r['label'] == 'UNCERTAIN')}")
    if synthetic:
        print("\n*** SYNTHETIC PREDICTIONS -- these numbers describe the harness, "
              "not the Router ***")
    print(f"\n{'thresh':>6} {'posted':>7} {'prec':>6} {'cover':>6} "
          f"{'false-silence':>14} {'missed':>7}")
    for t in THRESHOLDS:
        s = sweep(rows, preds, t)
        prec = "  n/a" if s["precision"] != s["precision"] else f"{s['precision']:.2f}"
        cov = "  n/a" if s["coverage"] != s["coverage"] else f"{s['coverage']:.2f}"
        print(f"{t:6.2f} {s['posted']:7d} {prec:>6} {cov:>6} "
              f"{s['false_on_silence']:>7d} ({s['false_on_silence_rows']:>3d}r) "
              f"{s['missed']:>7d}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("predictions", nargs="?")
    ap.add_argument("--stub", action="store_true")
    args = ap.parse_args()
    if not LABELLED.exists():
        print(f"{LABELLED} missing; run apply_labels.py first", file=sys.stderr)
        return 2

    rows = load_labelled()
    if args.stub:
        preds = stub_predictions(rows)
    elif args.predictions:
        preds = [json.loads(l) for l in
                 open(args.predictions, encoding="utf-8") if l.strip()]
    else:
        ap.error("give a predictions file, or --stub")
        return 2
    report(rows, preds, synthetic=args.stub)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
