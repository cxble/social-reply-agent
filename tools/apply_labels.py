"""Attach hand labels to a candidate set, and report what they say.

    python3 tools/apply_labels.py <set> labels/<set>.tsv     # merge
    python3 tools/apply_labels.py <set> --report             # distribution

`<set>` is `random` or `boundary` under `data/candidates/`. The label file is
`nid<TAB>label<TAB>note`, one line per labelled Comment; the note is optional and
is where a boundary call gets its reason. Only the labelled lines are touched, so
labelling can be done in tranches and the file merged repeatedly.

The vocabulary is pinned below. That is deliberate: a typo (`DOA_BLESING`) would
otherwise silently become a thirteenth class and quietly split a real one, and the
counts are the entire output of this exercise. An unknown label is an error.

VOCABULARY -- the eleven Intents of the reply table, plus two non-Intents:

  NO_REPLY   matches nothing and is *correctly* answered with nothing -- ADR 0018.
             Distinct from OUT_OF_SCOPE, which is a Comment no Canned reply fits -- the
             difference is whether the omission is the design working or the design
             failing, and only the labels tell them apart. Named NO_REPLY rather than
             TAIL because the glossary's Tail is the *gap*, which is the opposite.
  UNCERTAIN  the reading is genuinely undecided. Kept, not hidden: a large
             UNCERTAIN count is a finding about the Intent set, and forcing a
             guess would destroy exactly the information this set exists to hold.
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

CANDIDATES = Path("data/candidates")

INTENTS = [
    "DOA_BLESSING", "DOA_REQUEST", "GREETING", "PRAISE_ENCOURAGE",
    "BENEFICIARY_THANKS", "HELP_REQUEST", "JOIN_ENQUIRY", "CONVERT_CONGRATS",
    "DONATION_ENQUIRY", "ZAKAT_SEDEKAH_ENQUIRY", "OUT_OF_SCOPE",
]
NON_INTENTS = ["NO_REPLY", "UNCERTAIN"]
VOCAB = INTENTS + NON_INTENTS


def load(set_name: str) -> list[dict]:
    return [json.loads(l) for l in
            (CANDIDATES / f"{set_name}.jsonl").open(encoding="utf-8") if l.strip()]


def read_labels(path: Path) -> dict[str, tuple[str, str]]:
    out: dict[str, tuple[str, str]] = {}
    for lineno, line in enumerate(path.open(encoding="utf-8"), 1):
        line = line.rstrip("\n")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            print(f"{path}:{lineno}: need `nid<TAB>label`", file=sys.stderr)
            raise SystemExit(2)
        nid, label = parts[0].strip(), parts[1].strip()
        note = parts[2].strip() if len(parts) > 2 else ""
        if label not in VOCAB:
            print(f"{path}:{lineno}: unknown label {label!r}", file=sys.stderr)
            raise SystemExit(2)
        out[nid] = (label, note)
    return out


def merge(set_name: str, labels_path: Path) -> int:
    rows = load(set_name)
    labels = read_labels(labels_path)
    known = {r["nid"] for r in rows}
    unknown = sorted(set(labels) - known)
    if unknown:
        print(f"{len(unknown)} label(s) match no candidate in {set_name}: "
              f"{', '.join(unknown[:5])}", file=sys.stderr)
        raise SystemExit(2)

    for r in rows:
        if r["nid"] in labels:
            r["label"], r["note"] = labels[r["nid"]]

    out = CANDIDATES / f"{set_name}.labelled.jsonl"
    with out.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    done = sum(1 for r in rows if r["label"])
    print(f"{set_name}: {done}/{len(rows)} labelled -> {out}")
    return 0


def report(set_name: str) -> int:
    path = CANDIDATES / f"{set_name}.labelled.jsonl"
    if not path.exists():
        print(f"{path} does not exist; merge labels first", file=sys.stderr)
        return 2
    rows = [json.loads(l) for l in path.open(encoding="utf-8") if l.strip()]

    labelled = [r for r in rows if r["label"]]
    print(f"{set_name}: {len(labelled)}/{len(rows)} labelled\n")

    print(f"{'label':22s} {'distinct':>8s} {'rows':>6s}")
    agg: dict[str, list[int]] = collections.defaultdict(lambda: [0, 0])
    for r in labelled:
        agg[r["label"]][0] += 1
        agg[r["label"]][1] += r["rows"]
    for label, (d, n) in sorted(agg.items(), key=lambda kv: -kv[1][1]):
        print(f"{label:22s} {d:8d} {n:6d}")
    print(f"{'unlabelled':22s} {len(rows) - len(labelled):8d} "
          f"{sum(r['rows'] for r in rows if not r['label']):6d}")

    uncertain = [r for r in labelled if r["label"] == "UNCERTAIN"]
    if uncertain:
        print(f"\nUNCERTAIN ({len(uncertain)} distinct, "
              f"{sum(r['rows'] for r in uncertain)} rows) -- the Intent set's own test:")
        for r in sorted(uncertain, key=lambda x: -x["rows"])[:20]:
            print(f"  {r['rows']:4d}x  {r['norm'][:70]}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("set_name", choices=["random", "boundary"])
    ap.add_argument("labels", nargs="?", help="TSV to merge")
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()
    if args.report:
        return report(args.set_name)
    if not args.labels:
        ap.error("give a labels TSV to merge, or --report")
    return merge(args.set_name, Path(args.labels))


if __name__ == "__main__":
    raise SystemExit(main())
