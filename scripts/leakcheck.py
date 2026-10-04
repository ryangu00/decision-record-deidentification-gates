#!/usr/bin/env python3
"""leakcheck.py — semantic label-leak filter for free-text-option rows (ARCH).

For each row whose options are free text, ask the local model a yes/no question:
"Does the CONTEXT reveal, state, or strongly imply which of the OPTIONS was chosen or which were rejected?"
Read the first-token logprobs for Yes/No; if p(Yes) >= --threshold (default 0.5) the row is marked
leak=True and dropped from --out (kept in --dropped). Three reads, median, to ride over server noise.
Usage: leakcheck.py --in FILE --out FILE --dropped FILE [--threshold 0.5] [--reps 3] [--base URL] [--model M]
"""
import argparse, json, math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from decidability import chat_logprobs, first_token_top_logprobs  # noqa: E402

from common import load_config
ap = argparse.ArgumentParser()
ap.add_argument("--in", dest="inp", required=True); ap.add_argument("--out", required=True); ap.add_argument("--dropped", required=True)
ap.add_argument("--threshold", type=float, default=0.5); ap.add_argument("--reps", type=int, default=3)
ap.add_argument("--base", default="http://127.0.0.1:8000/v1"); ap.add_argument("--model", default="local-model")
ap.add_argument("--config")
a = ap.parse_args()
FIXED = set(load_config(a.config)["lanes"] + ["APPLY", "REJECT"])

SYS = "You are a strict auditor. Answer with exactly one word: Yes or No."
def p_yes(state, options):
    user = ("CONTEXT:\n" + state + "\n\nOPTIONS:\n" + "\n".join(f"- {o}" for o in options) +
            "\n\nDoes the CONTEXT reveal, state, or strongly imply which option was chosen, adopted, approved, or which options were rejected? Answer Yes or No.")
    ps = []
    for _ in range(a.reps):
        data, ok = chat_logprobs(a.base, a.model, SYS, user)
        tl = first_token_top_logprobs(data) if ok else []
        if not tl: continue
        d = {}
        for tok, lp in tl:
            k = tok.strip().lower()
            if k in ("yes", "no"): d[k] = max(d.get(k, -1e9), lp)
        if not d: continue
        floor = min(lp for _, lp in tl) - 3.0
        y, n = d.get("yes", floor), d.get("no", floor)
        mx = max(y, n)
        ps.append(math.exp(y - mx) / (math.exp(y - mx) + math.exp(n - mx)))
    return (sorted(ps)[len(ps) // 2] if ps else None), ps

kept = dropped = skipped = 0
with open(a.inp) as f, open(a.out, "w") as o, open(a.dropped, "w") as dr:
    for line in f:
        r = json.loads(line)
        if r.get("scrub_failed"):
            dr.write(line); dropped += 1; continue
        if set(r["options"]) <= FIXED:
            o.write(line); kept += 1; skipped += 1; continue
        p, ps = p_yes(r["state"], r["options"])
        r["leak_p_yes"] = p; r["leak_reads"] = ps
        if p is None or len(ps) != a.reps or p >= a.threshold:
            r["leak"] = True; dr.write(json.dumps(r, ensure_ascii=False) + "\n"); dropped += 1
        else:
            o.write(json.dumps(r, ensure_ascii=False) + "\n"); kept += 1
        print(f"{r['id']} p_yes={p} {'DROP' if r.get('leak') else 'keep'}", file=sys.stderr, flush=True)
print(f"kept {kept} (of which fixed-vocab pass-through {skipped}) | dropped as leaks {dropped}", file=sys.stderr)
