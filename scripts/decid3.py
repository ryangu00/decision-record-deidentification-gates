#!/usr/bin/env python3
"""Repeated-read gate, with explicitly optional post-run improvements.

Historical defaults: raw options on both sides, first raw pair as the floor.
New options: delivered options, stability report, mean of three raw pairs.
All modes reject empty comparisons, missing reads and incompatible options.
"""
import argparse
import collections
import itertools
import json
import random
from pathlib import Path

from common import read_rows, write_rows
from decidability import (PLACEHOLDER_RE, build_user, chat_logprobs,
                          first_token_top_logprobs, top_letter)


def majority(reads):
    # Historical tie rule: first observed among equally frequent letters.
    return collections.Counter(reads).most_common(1)[0][0]


def summarize(rows, floor_estimator="pair"):
    if not rows:
        raise ValueError("No comparable rows")
    n = len(rows)
    raw_counts = collections.Counter(row["raw_maj"] for row in rows)
    scrub_counts = collections.Counter(row["scrub_maj"] for row in rows)
    result = {
        "n": n,
        "agreement": sum(row["agree"] for row in rows) / n,
        "pair_floor": sum(row["self_floor_pair"] for row in rows) / n,
        "mean_pairs_floor": sum(row["self_floor_mean_pairs"] for row in rows) / n,
        "raw_marginals": dict(raw_counts),
        "scrubbed_marginals": dict(scrub_counts),
        "chance_agreement": sum(raw_counts[k] * scrub_counts[k]
                                for k in raw_counts) / n ** 2,
    }
    result["floor"] = result["pair_floor" if floor_estimator == "pair"
                             else "mean_pairs_floor"]
    result["stability"] = {}
    for name, stable in (("unanimous", True), ("split", False)):
        subset = [r for r in rows if r["raw_unanimous"] == stable]
        result["stability"][name] = {
            "n": len(subset),
            "agreement": sum(r["agree"] for r in subset) / len(subset)
            if subset else None,
        }
    result["flips_by_class"] = dict(collections.Counter(
        c for r in rows if not r["agree"] for c in (r["classes"] or ["(none)"])))
    return result


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--raw", type=Path, required=True)
    ap.add_argument("--scrubbed", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--summary", type=Path)
    ap.add_argument("--per-gate", type=int, default=40)
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--slack", type=float, default=0.05)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--base", default="http://127.0.0.1:8000/v1")
    ap.add_argument("--model", default="local-model")
    ap.add_argument("--scrubbed-options", action="store_true")
    ap.add_argument("--stability-report", action="store_true")
    ap.add_argument("--floor-estimator", choices=("pair", "mean-pairs"), default="pair")
    a = ap.parse_args(argv)
    if a.reps < 2 or a.per_gate < 1 or not 0 <= a.slack <= 1:
        ap.error("Require reps >= 2, per-gate >= 1 and slack in [0, 1]")
    if a.floor_estimator == "mean-pairs" and a.reps != 3:
        ap.error("mean-pairs requires exactly three reads")
    raw = {r["id"]: r for r in read_rows(a.raw)}
    scrubbed = {r["id"]: r for r in read_rows(a.scrubbed)
                if not r.get("scrub_failed") and not r.get("leak")}
    if not scrubbed or set(scrubbed) - set(raw):
        raise ValueError("Empty data or scrubbed rows without raw counterparts")
    by_class = collections.defaultdict(list)
    for rid in sorted(scrubbed):
        by_class[raw[rid]["gate"]].append(rid)
    rng = random.Random(a.seed)
    sample = []
    for _, ids in sorted(by_class.items()):
        rng.shuffle(ids)
        sample.extend(ids[:a.per_gate])

    def reads(state, question, options):
        valid = {chr(65 + i) for i in range(len(options) + 1)}
        out = []
        for _ in range(a.reps):
            data, ok = chat_logprobs(a.base, a.model,
                                    "You answer with exactly one capital letter.",
                                    build_user(state, question, options))
            letter = top_letter(first_token_top_logprobs(data), valid) if ok else None
            if letter is None:
                raise ValueError("Missing first-token option logprobs; gate cannot pass")
            out.append(letter)
        return out

    rows = []
    for rid in sample:
        r, s = raw[rid], scrubbed[rid]
        options = r["options"]
        delivered = s["options"]
        if (not options or len(options) != len(delivered)
                or len(set(delivered)) != len(delivered)
                or r["gate"] != s["gate"]):
            raise ValueError("Options must retain distinct positional correspondence")
        rr = reads(r["state"], r["question"], options)
        sr = reads(s["state"], s["question"], delivered if a.scrubbed_options else options)
        pairs = list(itertools.combinations(rr, 2))
        rm, sm = majority(rr), majority(sr)
        rows.append({"id": rid, "gate": r["gate"], "raw_reads": rr,
                     "scrub_reads": sr, "raw_maj": rm, "scrub_maj": sm,
                     "agree": rm == sm, "self_floor_pair": rr[0] == rr[1],
                     "self_floor_mean_pairs": sum(x == y for x, y in pairs) / len(pairs),
                     "raw_unanimous": len(set(rr)) == 1,
                     "classes": sorted(set(PLACEHOLDER_RE.findall(s["state"])) )})
    write_rows(a.out, rows)
    reports = {}
    for cls in sorted(by_class):
        report = summarize([r for r in rows if r["gate"] == cls], a.floor_estimator)
        report["pass"] = report["agreement"] >= report["floor"] - a.slack
        reports[cls] = report
        print(f"{cls}: n={report['n']} agreement={report['agreement']:.3f} "
              f"floor={report['floor']:.3f} {'PASS' if report['pass'] else 'FAIL'}")
        print(f"{cls}: chance={report['chance_agreement']:.3f} "
              f"raw={report['raw_marginals']} scrubbed={report['scrubbed_marginals']} "
              f"flips={report['flips_by_class']}")
        if a.stability_report:
            print(f"{cls}: stability={report['stability']}")
    if a.summary:
        a.summary.write_text(json.dumps({"floor_estimator": a.floor_estimator,
                                         "scrubbed_options": a.scrubbed_options,
                                         "classes": reports}, indent=2) + "\n")
    passed = all(r["pass"] for r in reports.values())
    print("DECIDABILITY " + ("PASS" if passed else "FAIL"))
    return 0 if passed else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, KeyError, OSError) as exc:
        print(f"DECIDABILITY FAIL: {type(exc).__name__}")
        raise SystemExit(2)
