#!/usr/bin/env python3
"""Build the recorded ROUTE ablation variants; no inference or claim of causality."""
import argparse
import re
from pathlib import Path

from common import load_config, read_rows, write_rows


def variants(raw, scrubbed, code_pattern):
    goal = re.compile(r"^Goal: .*$", re.M)
    code_re = re.compile(code_pattern)
    codes, output = {}, {"v1": [], "v2": [], "v3": []}

    def replace_code(match):
        text = match.group(0)
        if text not in codes:
            codes[text] = f"ref_{len(codes) + 1}"
        return codes[text]

    for r in raw:
        s = scrubbed.get(r["id"])
        if r["gate"] != "ROUTE" or not s or s.get("scrub_failed"):
            continue
        gr, gs = goal.search(r["state"]), goal.search(s["state"])
        if not gr or not gs:
            continue
        output["v1"].append({**s, "state": goal.sub(lambda _: gs.group(), r["state"], count=1)})
        output["v2"].append({**s, "state": code_re.sub(replace_code, r["state"])})
        output["v3"].append({**s, "state": goal.sub(lambda _: gr.group(), s["state"], count=1)})
    return output


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--raw", required=True)
    ap.add_argument("--scrubbed", required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--config")
    a = ap.parse_args()
    out = variants(read_rows(a.raw), {r["id"]: r for r in read_rows(a.scrubbed)},
                   load_config(a.config)["code_pattern"])
    for name, rows in out.items():
        write_rows(a.out_dir / (name + ".jsonl"), rows)
    print(f"ABLATION rows={len(out['v1'])}")


if __name__ == "__main__":
    main()
