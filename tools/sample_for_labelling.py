"""Draw the hand-labelled set used to calibrate `minimum_match_threshold`.

    python3 tools/sample_for_labelling.py --report
    python3 tools/sample_for_labelling.py --draw 400 250

Reads `data/corpus.jsonl` (gitignored -- see tools/prepare_corpus.py) and writes
candidate files under `data/candidates/`.

The labelling unit is the **distinct Normalized Comment**, not the row: 1,423 rows
are 839 distinct Comments, and `alhamdulillah` is one decision rather than 114.
Row counts are kept per candidate so a label can be weighted back to the corpus.

Two sets, drawn separately, because they answer different questions:

  * `boundary` -- every distinct Comment in the families where Intents collide
    (`tolong doa` vs a plea, `nak mohon` vs `nak sertai`, `fitrah`/`sedekah` vs
    money, a third party's illness inside a blessing, bare formulae, `bantu`).
    Enriched on purpose. It answers *where the boundary is*, and its mix is not
    the corpus's mix, so no base rate may be computed from it.
  * `random` -- a sample stratified by Post, weighted to rows. It answers *how
    often*, and it is the only set from which precision at a threshold may be
    read.

Mixing them would make every rate wrong. Keeping them apart is the whole design.

Sampling is seeded and therefore reproducible; `--draw` replaces the files.

Labels are added by hand, not by any matcher in this repo -- that is the point of
the set. A candidate starts with `label: null`.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import random
import re
import sys
from pathlib import Path

from normalize import bare_interjection, is_empty

CORPUS = Path("data/corpus.jsonl")
OUT = Path("data/candidates")

# Families where two Intents collide, or where an Intent is easy to invent. Each
# is a regex over the Normalized Comment. A Comment may be in several.
FAMILIES: list[tuple[str, str]] = [
    ("doa-request-form", r"\bdoa kan\b|\btolong doa\b|\bminta doa\b|\bmohon doa\b|\bdoa untuk\b"),
    ("join-vs-help", r"\bnak join\b|\bnak sertai\b|\bnk join\b|\bsertai\b|\bjadi ahli\b|\bmohon\b"),
    ("zakat-words", r"\bfitrah\b|\bsedekah\b|\binfaq\b|\bzakat\b"),
    ("third-party-illness", r"sembuh|shifak|syafakallah|sihat"),
    ("bantu-family", r"\bbantu\b|\btolong\b"),
    ("thanks-family", r"\bterima kasih\b|\bt kasih\b|\btkasih\b|\btrm ksh\b|\btq\b|\bthank\b"),
    ("donate-words", r"\bsumbang\b|\bderma\b|\bakaun\b|\baccount\b"),
    ("convert-words", r"\bmasuk islam\b|\bmualaf\b|\bsyahadah\b|\bfitrah\b|\bhidayah\b"),
    ("greeting-only", r"^\s*salam\b"),
    ("praise-family", r"\bterbaik\b|\bmantap\b|\bbagus\b|\bhebat\b|\bsyabas\b|\btabik\b|keep it up"),
    ("english-words", r"\b(the|you|your|with|may|for|thank|keep|praise|bless|heart|please|help|good|job|well|done)\b"),
    ("how-to-help", r"macam mana nak bantu|mcm mana nak bantu|cara nak bantu|camna cara|mcm mna nak bant"),
]

EXTRA = ("bare-formula", "empty-text")


def candidates_by_norm(rows: list[dict]) -> dict[str, dict]:
    """One entry per distinct Normalized Comment, carrying its own row count."""
    out: dict[str, dict] = {}
    for r in rows:
        n = r["norm"]
        e = out.setdefault(n, {"norm": n, "rows": 0, "posts": collections.Counter(),
                               "texts": collections.Counter(), "families": set()})
        e["rows"] += 1
        e["posts"][r["post"]] += 1
        e["texts"][r["text"]] += 1
    for e in out.values():
        for name, pat in FAMILIES:
            if re.search(pat, e["norm"]):
                e["families"].add(name)
        if bare_interjection(e["norm"]):
            e["families"].add("bare-formula")
        if is_empty(e["norm"]):
            e["families"].add("empty-text")
    return out


def norm_id(norm: str) -> str:
    return "n" + hashlib.sha1(norm.encode("utf-8")).hexdigest()[:8]


def report(by_norm: dict[str, dict]) -> None:
    rows = sum(e["rows"] for e in by_norm.values())
    print(f"distinct Comments {len(by_norm)}  rows {rows}")
    print(f"\n{'family':22s} {'distinct':>8s} {'rows':>6s}")
    counts: dict[str, list[int]] = collections.defaultdict(lambda: [0, 0])
    for e in by_norm.values():
        for f in e["families"]:
            counts[f][0] += 1
            counts[f][1] += e["rows"]
    for f in [n for n, _ in FAMILIES] + list(EXTRA):
        d, r = counts[f]
        print(f"{f:22s} {d:8d} {r:6d}")
    in_any = sum(1 for e in by_norm.values() if e["families"])
    print(f"\nin no family: {len(by_norm) - in_any} distinct Comments "
          f"({rows - sum(e['rows'] for e in by_norm.values() if e['families'])} rows)")


def write(name: str, picked: list[dict]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{name}.jsonl"
    with path.open("w", encoding="utf-8") as fh:
        for e in sorted(picked, key=lambda x: (-x["rows"], x["norm"])):
            fh.write(json.dumps({
                "nid": norm_id(e["norm"]),
                "norm": e["norm"],
                "text": e["texts"].most_common(1)[0][0],
                "rows": e["rows"],
                "posts": [p for p, _ in e["posts"].most_common()],
                "families": sorted(e["families"]),
                "label": None,
                "note": None,
            }, ensure_ascii=False) + "\n")
    print(f"wrote {len(picked)} candidates -> {path}")


def draw_boundary(by_norm: dict[str, dict], cap: int) -> list[dict]:
    """Every contested Comment, most-repeated first, up to `cap` per family."""
    picked: dict[str, dict] = {}
    for name, _ in FAMILIES:
        members = sorted((e for e in by_norm.values() if name in e["families"]),
                         key=lambda x: -x["rows"])
        for e in members[:cap]:
            picked[e["norm"]] = e
    for name in EXTRA:
        members = sorted((e for e in by_norm.values() if name in e["families"]),
                         key=lambda x: -x["rows"])
        for e in members[:cap]:
            picked[e["norm"]] = e
    return list(picked.values())


def draw_random(by_norm: dict[str, dict], n: int, seed: int = 20261021) -> list[dict]:
    """Distinct Comments drawn per Post in proportion to that Post's rows."""
    rng = random.Random(seed)
    per_post: dict[str, list[dict]] = collections.defaultdict(list)
    for e in by_norm.values():
        # assign each distinct Comment to the Post it mostly appears on
        per_post[e["posts"].most_common(1)[0][0]].append(e)
    total_rows = sum(e["rows"] for e in by_norm.values())
    picked: list[dict] = []
    for post, members in per_post.items():
        post_rows = sum(e["rows"] for e in members)
        want = max(1, round(n * post_rows / total_rows))
        rng.shuffle(members)
        picked += members[:want]
    return picked


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default=str(CORPUS))
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--draw", nargs=2, type=int, metavar=("RANDOM", "PER_FAMILY"))
    args = ap.parse_args()

    rows = [json.loads(l) for l in open(args.corpus, encoding="utf-8") if l.strip()]
    by_norm = candidates_by_norm(rows)

    if args.report or not args.draw:
        report(by_norm)
    if args.draw:
        n_random, cap = args.draw
        write("random", draw_random(by_norm, n_random))
        write("boundary", draw_boundary(by_norm, cap))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
