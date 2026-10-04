#!/usr/bin/env python3
"""postscrub.py — deterministic clean-up after the model scrub, then a case-insensitive mechanical gate re-check.

Fixes found by the first audit:
  * day-of-month residue next to month placeholders (month-YYYY-MM-18 -> month-YYYY-MM; month-2024-05-18 -> month-2024-05)
  * ROUTE rows: the whole Goal value (an internal goal slug) becomes one project_N placeholder from the shared map
  * known internal tokens the model tends to keep (passed via --tokens FILE, one per line: token<TAB>class) -> class placeholder
  * mechanical gate re-check over state + options + label with the patterns file, case-insensitive; failures marked scrub_failed
Usage: postscrub.py --in FILE --out FILE --map FILE --patterns FILE [--tokens FILE]
"""
import argparse, json, re, sys
ap = argparse.ArgumentParser()
ap.add_argument("--in", dest="inp", required=True); ap.add_argument("--out", required=True)
ap.add_argument("--map", required=True); ap.add_argument("--patterns", required=True); ap.add_argument("--tokens")
ap.add_argument("--goal-pattern", help="Regex with prefix and value capture groups")
ap.add_argument("--config")
a = ap.parse_args()
from common import load_config, load_patterns
config = load_config(a.config)

m = json.load(open(a.map)); changed = False
def nxt(cls):
    n = max([int(mm.group(1)) for v in m.values() for mm in [re.match(cls + r"_(\d+)$", v)] if mm] + [0]) + 1
    return f"{cls}_{n}"
def ph(entity, cls):
    global changed
    if entity not in m:
        low = [k for k in m if k.lower() == entity.lower()]
        m[entity] = m[low[0]] if low else nxt(cls); changed = True
    return m[entity]

tokens = []
if a.tokens:
    for line in open(a.tokens):
        line = line.rstrip("\n")
        if not line or line.startswith("#"): continue
        t, cls = line.split("\t")[:2]; tokens.append((t, cls))
pats = load_patterns(a.patterns)
DAY = re.compile(r"((?:month-)?(?:\d{4}|YYYY)-(?:\d{2}|MM))[-/ ](?:\d{1,2})(?!\d)")
GOAL = re.compile(a.goal_pattern or config["goal_pattern"], re.M)
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+){2,}$")

def fix_text(s, gate):
    s = DAY.sub(r"\1", s)
    if gate == "ROUTE":
        def goal_sub(mo):
            v = mo.group(2)
            if re.match(r"^(project|bot|persona|node|person|vendor|id)_\d+$", v):
                return mo.group(0)
            return mo.group(1) + ph(v, "project")
        s = GOAL.sub(goal_sub, s)
    for t, cls in tokens:
        if re.search(re.escape(t), s, re.I):
            s = re.sub(re.escape(t), ph(t, cls), s, flags=re.I)
    return s

n = 0; fixed = 0; failed = 0; failed_by = {}
with open(a.inp) as f, open(a.out, "w") as o:
    for line in f:
        r = json.loads(line); n += 1
        if r.get("scrub_failed"):
            o.write(json.dumps(r, ensure_ascii=False) + "\n"); failed += 1; continue
        before = (r["state"], list(r["options"]), r["label"])
        r["state"] = fix_text(r["state"], r.get("gate"))
        r["options"] = [fix_text(x, r.get("gate")) for x in r["options"]]
        r["label"] = fix_text(r["label"], r.get("gate"))
        if r["label"] not in r["options"]:
            r["scrub_failed"] = True; r["fail_reason"] = "label_not_in_options_after_postscrub"; failed += 1
        else:
            blob = "\n".join([r["state"], *r["options"], r["label"]])
            hit = [i for i, p in enumerate(pats) if p.search(blob)]
            if hit:
                r["scrub_failed"] = True; r["fail_reason"] = f"mechanical_ci:{hit}"; failed += 1
                for i in hit: failed_by[i] = failed_by.get(i, 0) + 1
            elif (r["state"], r["options"], r["label"]) != before:
                fixed += 1
        o.write(json.dumps(r, ensure_ascii=False) + "\n")
if changed: json.dump(m, open(a.map, "w"), ensure_ascii=False, indent=1)
print(f"rows {n} | changed by post-pass {fixed} | failed (incl. earlier) {failed} | mechanical (case-insensitive) failures by pattern {failed_by} | map entries {len(m)}", file=sys.stderr)
