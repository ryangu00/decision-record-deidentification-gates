#!/usr/bin/env python3
r"""mapclean.py — repair a poisoned entity->placeholder map and reverse its damage in scrubbed rows.

The model-emitted entities were merged without validation, so the map contains: malformed placeholders
(word-glued placeholders, project_N, day-level dates, paths), public product names (MTP, Qwen, vLLM ...),
generic words (bot, node, project, persona) that were then replaced INSIDE other words, and duplicates.

This script:
  1. keeps only entries whose placeholder matches ^(project|bot|persona|node|person|vendor|id)_\d+$ or month-YYYY-MM / month-\d{4}-\d{2},
     whose original is >= 4 characters, and whose original is not in the public keep-list;
  2. for every dropped entry, replaces its placeholder back with the original in all scrubbed rows (state, options, label);
  3. renames any literal unnumbered placeholder (project_N, bot_N, node_N, vendor_N, persona_N, id_N, person_N) to <class>_0 ("unknown");
  4. writes the cleaned map and the repaired rows.
Usage: mapclean.py --map FILE --in FILE --out FILE --map-out FILE [--keep FILE]
"""
import argparse, json, re, sys
ap = argparse.ArgumentParser()
ap.add_argument("--map", required=True); ap.add_argument("--in", dest="inp", required=True)
ap.add_argument("--out", required=True); ap.add_argument("--map-out", required=True); ap.add_argument("--keep")
a = ap.parse_args()

PH = re.compile(r"^(?:(?:project|bot|persona|node|person|vendor|id)_\d+|month-(?:\d{4}|YYYY)-(?:\d{2}|MM))$")
keep = set(x.strip().lower() for x in open(a.keep)) if a.keep else set()
m = json.load(open(a.map))
good, dropped = {}, {}
for orig, ph in m.items():
    if not PH.match(ph) or len(orig) < 4 or orig.lower() in keep or re.match(r"^(?:project|bot|persona|node|person|vendor|id)(?:_\w+)?$", orig, re.I):
        dropped[orig] = ph
    else:
        good[orig] = ph
# a placeholder kept for one original but also emitted for a dropped original: reversing would corrupt the kept one -> only reverse when unique to the dropped originals
kept_phs = set(good.values())
rev = [(ph, orig) for orig, ph in dropped.items() if ph not in kept_phs and PH.match(ph)]
rev.sort(key=lambda t: -len(t[0]))
UNNUM = re.compile(r"\b(project|bot|persona|node|person|vendor|id)_N\b")

def repair(s):
    for ph, orig in rev:
        s = s.replace(ph, orig)
    s = UNNUM.sub(lambda mo: mo.group(1) + "_0", s)
    return s

n = 0; changed = 0
with open(a.inp) as f, open(a.out, "w") as o:
    for line in f:
        r = json.loads(line); n += 1
        before = (r["state"], list(r["options"]), r["label"])
        r["state"] = repair(r["state"]); r["options"] = [repair(x) for x in r["options"]]; r["label"] = repair(r["label"])
        if (r["state"], r["options"], r["label"]) != before: changed += 1
        if r["label"] not in r["options"] and not r.get("scrub_failed"):
            r["scrub_failed"] = True; r["fail_reason"] = "label_not_in_options_after_mapclean"
        o.write(json.dumps(r, ensure_ascii=False) + "\n")
json.dump(good, open(a.map_out, "w"), ensure_ascii=False, indent=1)
print(f"map: kept {len(good)} dropped {len(dropped)} (reversed in text: {len(rev)}) | rows {n} changed {changed}", file=sys.stderr)
