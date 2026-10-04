#!/usr/bin/env python3
"""Seeded audit sample with class and REVIEW-verdict strata; no provenance."""
import argparse
import collections
import random

from common import read_rows, write_rows

FIELDS = ("id", "gate", "state", "question", "options", "label")


def select(rows, seed=23, size=50):
    rows = [r for r in rows if r.get("scrubbed") and not r.get("scrub_failed")
            and not r.get("leak")]
    if len(rows) < size:
        raise ValueError("Not enough usable rows for requested sample")
    rng = random.Random(seed)
    groups = collections.defaultdict(list)
    for row in rows:
        key = row["gate"] if row["gate"] != "REVIEW" else row["label"]
        groups[key].append(row)
    sample = []
    for key, limit in (("ROUTE", 17), ("APPLY", 8), ("REJECT", 8), ("ARCH", 17)):
        rng.shuffle(groups[key])
        sample.extend(groups[key][:limit])
    seen = {r["id"] for r in sample}
    remainder = [r for r in rows if r["id"] not in seen]
    rng.shuffle(remainder)
    sample = (sample + remainder)[:size]
    # Fresh sample identifiers avoid carrying source identifiers into review.
    return [{**{k: row[k] for k in FIELDS}, "id": f"sample-{i:06d}"}
            for i, row in enumerate(sample)]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=23)
    ap.add_argument("--size", type=int, default=50)
    a = ap.parse_args()
    sample = select(read_rows(a.inp), a.seed, a.size)
    write_rows(a.out, sample)
    print(f"SAMPLE rows={len(sample)} classes={dict(collections.Counter(r['gate'] for r in sample))}")


if __name__ == "__main__":
    main()
