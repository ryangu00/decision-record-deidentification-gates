#!/usr/bin/env python3
"""Deterministic repairs adapted from the recorded pipeline.
Codes become distinct ref_N placeholders; malformed placeholders are normalized.
Raw-text alignment restores configured severity tags and generic words.
REVIEW contexts are removed; ROUTE labels in state and duplicate options fail.
Private code, name, alias and severity rules are replaced by synthetic config.
"""
import argparse, difflib, json, re, sys
ap = argparse.ArgumentParser()
ap.add_argument("--in", dest="inp", required=True); ap.add_argument("--raw", required=True); ap.add_argument("--out", required=True)
ap.add_argument("--map", required=True); ap.add_argument("--codes"); ap.add_argument("--goal-desc")
ap.add_argument("--config")
a = ap.parse_args()
from common import load_config
config = load_config(a.config)
m = json.load(open(a.map)); map_changed = False
gdesc = json.load(open(a.goal_desc))["desc"] if a.goal_desc else {}
goal_of = {}  # ROUTE row id -> raw goal slug (for the description)
raw = {}
for line in open(a.raw):
    r = json.loads(line); raw[r["id"]] = r
def nxt(cls):
    return f"{cls}_{max([int(mm.group(1)) for v in m.values() for mm in [re.match(cls + r'_(\d+)$', v)] if mm] + [0]) + 1}"
def ph(entity, cls):
    global map_changed
    if entity not in m: m[entity] = nxt(cls); map_changed = True
    return m[entity]
CLS = r"(project|bot|persona|node|person|vendor|id)"
NESTED = re.compile(r"\b" + CLS + r"_N_?(\d+)\b"); DOUBLE = re.compile(r"\b" + CLS + r"_(\d+)_\d+\b")
PLURAL = re.compile(r"\b" + CLS + r"_Ns\b"); TRAIL = re.compile(r"\b" + CLS + r"_(\d+)[a-z]\b")
CODE = re.compile(config["code_pattern"])
NAMED = config["named_entities"]
ALIAS = re.compile(config["alias_pattern"]); LREF = re.compile(r":L\d+(?:-L?\d+)?")
CTX = re.compile(r"\n\s*Context:.*\Z", re.S); GOAL = re.compile(config["goal_pattern"], re.M)
TOK = re.compile(r"[A-Za-z0-9_./#-]+|[^\sA-Za-z0-9_]"); SEVERITY = re.compile(config["severity_pattern"])
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)+$")
codes = {}
def code(mo):
    s = mo.group(0)
    if s not in codes: codes[s] = f"ref_{len(codes) + 1}"
    return codes[s]
def fix(s, gate, rawgoal=None):
    s = NESTED.sub(r"\1_\2", s); s = DOUBLE.sub(r"\1_\2", s); s = PLURAL.sub(r"\1_0", s); s = TRAIL.sub(r"\1_\2", s)
    s = CODE.sub(code, s); s = ALIAS.sub("the local model", s); s = LREF.sub("", s)
    for name, cls in NAMED:
        if re.search(r"(?<![A-Za-z0-9_])" + re.escape(name) + r"(?![A-Za-z0-9_])", s): s = re.sub(r"(?<![A-Za-z0-9_])" + re.escape(name) + r"(?![A-Za-z0-9_])", ph(name, cls), s)
    if gate == "REVIEW": s = CTX.sub("", s)
    if gate == "ROUTE":
        s = GOAL.sub(lambda mo: mo.group(0) if re.fullmatch(r"project_\d+", mo.group(2)) else mo.group(1) + ph(mo.group(2), "project"), s)
        d = gdesc.get(rawgoal or "")
        if d: s = GOAL.sub(lambda mo: mo.group(1) + mo.group(2) + " (" + d + ")", s, count=1)
    return s
unb = {"severity": 0, "word": 0, "slug": 0}
def unbucket(scrub, rawtext):
    if "project_0" not in scrub or not rawtext: return scrub
    a_ = TOK.findall(CTX.sub("", rawtext)); b_ = TOK.findall(scrub); repl = {}
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(a=a_, b=b_, autojunk=False).get_opcodes():
        if tag != "replace" or "project_0" not in b_[j1:j2]: continue
        occ = b_[:j1].count("project_0") + b_[j1:j2].index("project_0"); orig = a_[i1:i2]
        rig = [t for t in orig if SEVERITY.match(t)]
        if rig: repl[occ] = rig[0]; unb["severity"] += 1
        elif len(orig) == 1 and orig[0] == "project": repl[occ] = "project"; unb["word"] += 1
        elif len(orig) == 1 and SLUG.match(orig[0]): repl[occ] = ph(orig[0], "project"); unb["slug"] += 1
    if not repl: return scrub
    c = [-1]
    def sub(mo):
        c[0] += 1; return repl.get(c[0], mo.group(0))
    return re.sub(r"\bproject_0\b", sub, scrub)
n = changed = 0; failed = {}
with open(a.inp) as f, open(a.out, "w") as o:
    for line in f:
        r = json.loads(line); n += 1
        if not r.get("scrub_failed"):
            before = (r["state"], list(r["options"]), r["label"]); g = r.get("gate"); rw = raw.get(r["id"], {})
            rg = re.search(r"^Goal: (.+?)\s*$", rw.get("state", ""), re.M); rawgoal = rg.group(1) if rg else None
            r["state"] = unbucket(fix(r["state"], g, rawgoal), rw.get("state", ""))
            ropts = rw.get("options", []); r["options"] = [unbucket(fix(x, g), ropts[i] if i < len(ropts) else "") for i, x in enumerate(r["options"])]
            r["label"] = unbucket(fix(r["label"], g), rw.get("label", ""))
            reason = None
            if r["label"] not in r["options"]: reason = "label_not_in_options_after_postscrub2"
            elif len(set(r["options"])) < len(r["options"]): reason = "duplicate_options_after_postscrub2"
            elif g == "ROUTE" and re.search(r"(?<![A-Za-z0-9_])" + re.escape(r["label"]) + r"(?![A-Za-z0-9_])", r["state"], re.I): reason = "label_in_state"
            if reason: r["scrub_failed"] = True; r["fail_reason"] = reason; failed[reason] = failed.get(reason, 0) + 1
            elif (r["state"], r["options"], r["label"]) != before: changed += 1
            if g == "REVIEW": r["extra"] = {**r.get("extra", {}), "context_dropped": True}
        o.write(json.dumps(r, ensure_ascii=False) + "\n")
if map_changed: json.dump(m, open(a.map, "w"), ensure_ascii=False, indent=1)
if a.codes: json.dump(codes, open(a.codes, "w"), ensure_ascii=False, indent=1)
print(f"rows {n} changed {changed} newly failed {failed} refs {len(codes)} map {len(m)} unbucketed {unb}", file=sys.stderr)
