"""Turn a raw harvest into the working corpus the labelling set is drawn from.

    python3 tools/prepare_corpus.py <raw-harvest.jsonl> data/corpus.jsonl

Two things this does beyond copying:

  1. **Drops `author` and `cid`.** The repo is public. A Comment's text is
     already public on the Platform, but a file that pairs 1,315 handles with
     their text, in one archive, is a different artifact from the Comments
     sitting on TikTok -- it aggregates people and it is indexed. Neither field
     is needed to label an Intent, so neither is carried.
  2. **Adds `norm`.** The labelling unit is the distinct Normalized Comment, not
     the row: `alhamdulillah` appears 114 times and is one decision, not 114. So
     `norm` is computed once here and the sampler dedupes on it.

Row ids are sequential in the order of the input file, so they are stable for a
given harvest and meaningless outside it. `norm` is the stable key.

Reads untrusted harvested data and writes it back out; run with the script's own
directory on the path, never from inside a data directory.
"""

from __future__ import annotations

import json
import sys

from normalize import normalize


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    raw_path, out_path = sys.argv[1], sys.argv[2]

    rows = [json.loads(line) for line in open(raw_path, encoding="utf-8") if line.strip()]
    top = [r for r in rows if str(r.get("reply_id") or "0") == "0"]

    with open(out_path, "w", encoding="utf-8") as fh:
        for i, r in enumerate(top, 1):
            fh.write(json.dumps({
                "id": f"c{i:04d}",
                "post": r["post"],
                "text": r["text"],
                "norm": normalize(r["text"]),
                "digg_count": r.get("digg_count"),
                "create_time": r.get("create_time"),
            }, ensure_ascii=False) + "\n")

    print(f"read {len(rows)} rows, kept {len(top)} top-level Comments -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
