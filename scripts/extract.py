#!/usr/bin/env python3
"""extract.py — turn historical decision records into labelled decision triples.

Sources: routing JSONL, review markdown tables, ADR markdown files.
Emits the common JSONL schema. Uses a local OpenAI-compatible chat endpoint
for ADR extraction only.
"""
import argparse
import hashlib
import json
import random
import re
import sys
import urllib.error
import urllib.request
from common import open_request
from pathlib import Path

# --- shared model client -----------------------------------------------------

def _post_json(base, payload, timeout=180):
    url = base.rstrip("/") + "/chat/completions"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with open_request(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def chat(base, model, messages, *, max_tokens, timeout=180, retries=2):
    """Call the model with fixed kwargs. Returns (text, ok)."""
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0,
        "max_tokens": max_tokens,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    last_err = None
    for _ in range(retries):
        try:
            data = _post_json(base, payload, timeout=timeout)
            return data["choices"][0]["message"]["content"], True
        except (urllib.error.URLError, urllib.error.HTTPError, KeyError,
                ValueError, TimeoutError) as e:
            last_err = e
            try:
                import time
                time.sleep(2)
            except Exception:
                pass
    return (f"MODEL_ERROR: {last_err}", False)


def first_json_block(text):
    """Return the first {...} balanced block, or None."""
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(text)):
        c = text[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                chunk = text[start:i + 1]
                try:
                    return json.loads(chunk)
                except json.JSONDecodeError:
                    return None
    return None


def chat_json(base, model, messages, *, max_tokens, timeout=180):
    """Ask the model for a single JSON object. Returns (obj, text, ok).

    On parse failure, retries once with the model's previous output appended
    and a "return only valid JSON" instruction.
    """
    instr = messages[:]
    text, ok = chat(base, model, instr, max_tokens=max_tokens, timeout=timeout)
    if not ok:
        return None, text, False
    obj = first_json_block(text)
    if obj is not None:
        return obj, text, True
    # retry once
    retry = instr + [
        {"role": "assistant", "content": text},
        {"role": "user",
         "content": "return only valid JSON (a single object, nothing else)"},
    ]
    text2, ok2 = chat(base, model, retry, max_tokens=max_tokens, timeout=timeout)
    if not ok2:
        return None, text2, False
    obj2 = first_json_block(text2)
    if obj2 is not None:
        return obj2, text2, True
    return None, text2, False


# --- routing source ----------------------------------------------------------

from common import load_config
CONFIG = load_config()
LANE_OPTIONS = CONFIG["lanes"]

# task field that is only a bare task id, e.g. t1 / t3b
_TASK_ID_RE = re.compile(r"^t\d+[a-z]?$")


def lookup_task_what(goals_dir, goal, task_id):
    """Find the <what> cell for task_id in DIR/<goal>.md tasks table.

    Table rows look like: | t1 | <what> | <route> | <accept> | <status> |
    Returns the <what> string, or None if the file or row is missing.
    Never returns the <route> or <status> cells.
    """
    if not goals_dir:
        return None
    fp = Path(goals_dir) / f"{goal}.md"
    if not fp.is_file():
        return None
    try:
        text = fp.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None
    for line in text.splitlines():
        if "|" not in line:
            continue
        cells = [c.strip() for c in line.split("|")]
        # split on leading/trailing | yields empty edges at both ends
        if cells and cells[0] == "":
            cells = cells[1:]
        if cells and cells[-1] == "":
            cells = cells[:-1]
        if len(cells) < 2:
            continue
        if cells[0] != task_id:
            continue
        what = cells[1]
        if what:
            return what
    return None


def norm_lane(actual):
    value = str(actual or "").lower()
    for lane, substrings in CONFIG["lane_rules"]:
        if any(token.lower() in value for token in substrings):
            return lane
    return "other"


def extract_routing(path, limit, provenance_file, counter, goals_dir=None):
    rows = []
    kept = 0
    enriched = 0
    skipped = []
    read = 0
    with open(path, "r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            read += 1
            if len(rows) >= limit:
                break
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                skipped.append((lineno, "bad json"))
                continue
            task = (obj.get("task") or "").strip()
            if not task:
                skipped.append((lineno, "empty task"))
                continue
            rid = f"route-{counter['n']:06d}"
            counter["n"] += 1
            goal = obj.get("goal", "")
            shape = obj.get("shape", "")
            declared = norm_lane(obj.get("declared"))
            actual = obj.get("actual")
            label = norm_lane(actual)
            extra = {
                "declared": declared,
                "result": obj.get("result"),
                "rework": obj.get("rework"),
                "route_changed": declared != norm_lane(actual),
            }
            what = None
            if _TASK_ID_RE.match(task):
                what = lookup_task_what(goals_dir, goal, task)
            if what is not None:
                state = (f"Task: {what}\n"
                         f"Shape: {shape}\n"
                         f"Goal: {goal}")
                extra["task_enriched"] = True
                extra["task_id"] = task
                enriched += 1
            else:
                state = (f"Task: {task}\n"
                         f"Shape: {shape}\n"
                         f"Goal: {goal}")
                if _TASK_ID_RE.match(task):
                    extra["task_enriched"] = False
            rows.append({
                "id": rid,
                "source": "routing",
                "gate": "ROUTE",
                "state": state,
                "question": "Which execution lane should take this task?",
                "options": list(LANE_OPTIONS),
                "label": label,
                "extra": extra,
                "provenance": {"file": provenance_file, "row": lineno},
            })
            kept += 1
    return rows, {"read": read, "kept": kept, "enriched": enriched,
                  "skipped": skipped}


# --- review source -----------------------------------------------------------

REVIEW_OPTIONS = ["APPLY", "REJECT"]

_LINE_REF_RE = re.compile(
    r"(?P<file>[A-Za-z0-9_./\-]+?)\s*:?\s*L(?P<line>\d+)"
    r"|L(?P<line2>\d+)\s*/\s*L(?P<line3>\d+)"
)


def derive_slug(review_filename):
    name = Path(review_filename).name
    if name.startswith("reconcile-"):
        name = name[len("reconcile-"):]
    if name.endswith(".md"):
        name = name[:-3]
    return name


def resolve_context_dirs(cookbooks_dir, review_map, slug):
    if review_map and slug in review_map:
        target = review_map[slug]
        cand = Path(cookbooks_dir) / target
        if cand.is_dir():
            return [cand]
    # fallback: match a cookbook dir whose name contains the slug token
    base = Path(cookbooks_dir)
    if base.is_dir():
        matches = [d for d in base.iterdir() if d.is_dir() and slug in d.name]
        if matches:
            return matches[:1]
    return []


def find_ref_file(search_dirs, ref_name):
    """ref_name like README / README.md / docs/foo.md -> matching file."""
    candidates = [ref_name, ref_name + ".md"]
    for d in search_dirs:
        for c in candidates:
            full = (d / c) if not ref_name.startswith("docs/") else (d / c)
            if full.is_file():
                return full
        # also walk for basename match
        name = Path(ref_name).name
        for c in [name, name + ".md"]:
            full = d / c
            if full.is_file():
                return full
        # recursive search as last resort
        for d2 in _walk(d):
            for c in candidates + [name, name + ".md"]:
                full = d2 / c
                if full.is_file():
                    return full
    return None


def _walk(d):
    out = []
    try:
        for p in sorted(d.rglob("*")):
            if p.is_dir():
                out.append(p)
    except Exception:
        pass
    return out


def read_lines_around(path, line_no, radius=1, max_lines=3):
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return []
    idx = line_no - 1
    if idx < 0 or idx >= len(lines):
        return []
    lo = max(0, idx - radius)
    hi = min(len(lines), idx + radius + 1)
    return lines[lo:hi][:max_lines]


def extract_review(review_dir, cookbooks_dir, review_map, limit, counter):
    rows = []
    kept = 0
    skipped = []
    files_seen = 0
    base = Path(review_dir)
    if not base.is_dir():
        return rows, {"read": 0, "kept": 0, "skipped": [],
                      "files": 0}
    files = sorted(p for p in base.iterdir() if p.is_file()
                   and p.suffix == ".md")
    for fp in files:
        if len(rows) >= limit:
            break
        files_seen += 1
        slug = derive_slug(fp.name)
        search_dirs = resolve_context_dirs(cookbooks_dir, review_map, slug) \
            if cookbooks_dir else []
        text = fp.read_text(encoding="utf-8", errors="replace")
        for lineno, line in enumerate(text.splitlines(), 1):
            if len(rows) >= limit:
                break
            if "|" not in line:
                continue
            cells = [c.strip() for c in line.split("|")]
            # leading/trailing empty from leading/trailing |
            cells = [c for c in cells if c != ""]
            # need: id? finding decision change  OR  finding decision change
            if len(cells) < 3:
                continue
            # find the decision cell (exactly APPLY or REJECT)
            dec_idx = None
            for i, c in enumerate(cells):
                if c in ("APPLY", "REJECT"):
                    dec_idx = i
                    break
            if dec_idx is None:
                continue
            # finding is the cell before decision; change is after (ignored)
            if dec_idx - 1 < 0:
                skipped.append((fp.name, lineno, "no finding cell"))
                continue
            finding = cells[dec_idx - 1]
            if not finding:
                skipped.append((fp.name, lineno, "empty finding"))
                continue
            decision = cells[dec_idx]
            # build context
            context_lines = []
            context_resolved = True
            refs = list(_LINE_REF_RE.finditer(finding))
            for m in refs:
                if m.group("line"):
                    ref_name = m.group("file")
                    line_no = int(m.group("line"))
                else:
                    # L13/L82 style: no file — skip file lookup
                    continue
                ref_file = find_ref_file(search_dirs, ref_name)
                if ref_file is None:
                    context_resolved = False
                    continue
                context_lines.extend(
                    read_lines_around(ref_file, line_no))
            rid = f"review-{counter['n']:06d}"
            counter["n"] += 1
            state = f"Reviewer finding: {finding}"
            if context_lines:
                state += "\nContext:\n" + "\n".join(context_lines[:3])
            extra = {}
            if not context_resolved:
                extra["context_resolved"] = False
            rows.append({
                "id": rid,
                "source": "review",
                "gate": "REVIEW",
                "state": state,
                "question": "Should the author apply this reviewer finding?",
                "options": list(REVIEW_OPTIONS),
                "label": decision,
                "extra": extra,
                "provenance": {"file": str(fp), "row": lineno},
            })
            kept += 1
    return rows, {"read": files_seen, "kept": kept, "skipped": skipped,
                  "files": files_seen}


# --- adr source --------------------------------------------------------------

def _longest_common_substring(a, b):
    """Length of the longest substring (chars) common to a and b."""
    if not a or not b:
        return 0
    prev = [0] * (len(b) + 1)
    best = 0
    for i in range(1, len(a) + 1):
        cur = [0] * (len(b) + 1)
        ai = a[i - 1]
        for j in range(1, len(b) + 1):
            if ai == b[j - 1]:
                cur[j] = prev[j - 1] + 1
                if cur[j] > best:
                    best = cur[j]
        prev = cur
    return best


_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")


def _label_token_overlap(state, label):
    """Fraction of label tokens (len>=3, lowercased) present in state."""
    toks = [t.lower() for t in _TOKEN_RE.findall(label) if len(t) >= 3]
    if not toks:
        return 0.0
    st = set(t.lower() for t in _TOKEN_RE.findall(state))
    hits = sum(1 for t in toks if t in st)
    return hits / len(toks)


def label_leaks(state, label):
    """True if the state leaks the label by substring or token overlap."""
    if not isinstance(state, str) or not isinstance(label, str):
        return False
    if _longest_common_substring(state, label) >= 25:
        return True
    if _label_token_overlap(state, label) >= 0.6:
        return True
    return False


def option_leak_log(state, options, label):
    """Return list of options (other than label) found verbatim (>=25 chars)
    in state when not all options are present. Empty list = nothing to log."""
    if not isinstance(state, str):
        return []
    present = []
    for o in options:
        if o == label:
            continue
        if isinstance(o, str) and len(o) >= 25 and o in state:
            present.append(o)
    if not present:
        return []
    # fine only if the label option (and thus all) is also in state
    if isinstance(label, str) and label in state:
        return []
    return present


def extract_adr(adr_dir, base, model, limit, counter):
    rows = []
    kept = 0
    skipped = []
    files_seen = 0
    option_leaks_logged = 0
    d = Path(adr_dir)
    if not d.is_dir():
        return rows, {"read": 0, "kept": 0, "skipped": [], "files": 0}
    files = sorted(p for p in d.iterdir() if p.is_file()
                   and p.suffix == ".md")
    for fp in files:
        if len(rows) >= limit:
            break
        files_seen += 1
        text = fp.read_text(encoding="utf-8", errors="replace")[:6000]
        prompt = (
            "You answer with a single JSON object and nothing else. "
            "Read this decision record and return JSON with keys: "
            '"context" (a 2-4 sentence English description of the situation, '
            "constraints, evidence, and the competing options AS OF BEFORE the "
            "decision, in neutral language). "
            "Do not state, hint at, or paraphrase which option was chosen; do "
            "not use phrases like 'the team decided', 'the decision was', 'it "
            "was chosen', 'was adopted', 'rolled back', or 'conditional pass'. "
            "No names of people, machines, projects or products beyond generic "
            "descriptions. "
            '"options" (an array of strings: first the chosen decision as one '
            "line, then each alternative the record names, one line each), "
            '"label" (the chosen option text, verbatim from options), '
            '"alternatives_named" (integer count of alternatives). '
            "Return only the JSON object.\n\nRECORD:\n" + text
        )
        messages = [{"role": "user", "content": prompt}]
        obj, raw, ok = chat_json(base, model, messages, max_tokens=900)
        if not ok or obj is None:
            skipped.append((fp.name, f"model/parse failure: {raw[:80]}"))
            continue
        options = obj.get("options")
        label = obj.get("label")
        context = obj.get("context", "")
        alts = obj.get("alternatives_named")
        if not isinstance(options, list) or len(options) < 2:
            skipped.append((fp.name, "fewer than 2 options"))
            continue
        if not isinstance(label, str) or label not in options:
            skipped.append((fp.name, "label not in options"))
            continue
        # leakage filter: if context reveals the label, retry once
        if label_leaks(context, label):
            retry_msgs = messages + [
                {"role": "user",
                 "content": "Your previous context revealed the decision; "
                 "rewrite the context without it."},
            ]
            obj2, raw2, ok2 = chat_json(base, model, retry_msgs,
                                       max_tokens=900)
            if ok2 and obj2 is not None:
                o2 = obj2.get("options")
                l2 = obj2.get("label")
                c2 = obj2.get("context", "")
                if (isinstance(o2, list) and len(o2) >= 2
                        and isinstance(l2, str) and l2 in o2):
                    options = o2
                    label = l2
                    context = c2
                    if not label_leaks(context, label):
                        # retry fixed the leak
                        pass
                    else:
                        skipped.append((fp.name, "label_leak"))
                        continue
                else:
                    skipped.append((fp.name, "label_leak"))
                    continue
            else:
                skipped.append((fp.name, "label_leak"))
                continue
        # option leakage: log if a non-label option appears verbatim but not
        # all options do
        leaked_opts = option_leak_log(context, options, label)
        if leaked_opts:
            option_leaks_logged += 1
        # seeded shuffle (deterministic per file content)
        seed = int(hashlib.sha1(text.encode("utf-8")).hexdigest(), 16) \
            % (2 ** 31)
        rng = random.Random(seed)
        pairs = list(zip(options, [o == label for o in options]))
        rng.shuffle(pairs)
        new_options = [p[0] for p in pairs]
        new_label = next(p[0] for p in pairs if p[1])
        rid = f"arch-{counter['n']:06d}"
        counter["n"] += 1
        rows.append({
            "id": rid,
            "source": "adr",
            "gate": "ARCH",
            "state": context,
            "question": "Which option did the team choose?",
            "options": new_options,
            "label": new_label,
            "extra": {
                "alternatives_named": alts,
                "option_leak": [o[:60] for o in leaked_opts],
            },
            "provenance": {"file": str(fp), "row": 1},
        })
        kept += 1
    return rows, {"read": files_seen, "kept": kept, "skipped": skipped,
                  "files": files_seen, "option_leaks": option_leaks_logged}


# --- main --------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(description="Extract decision triples.")
    ap.add_argument("--routing", type=Path)
    ap.add_argument("--reviews", type=Path)
    ap.add_argument("--cookbooks", type=Path)
    ap.add_argument("--review-map", type=Path,
                    help="JSON {slug: cookbook dir name}")
    ap.add_argument("--adr", type=Path)
    ap.add_argument("--goals", type=Path,
                    help="DIR of <goal>.md files for task-id enrichment")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--limit", type=int, default=1000)
    ap.add_argument("--sources", default="routing,review,adr")
    ap.add_argument("--base", default="http://127.0.0.1:8000/v1")
    ap.add_argument("--model", default="local-model")
    ap.add_argument("--config", type=Path)
    args = ap.parse_args(argv)
    global CONFIG, LANE_OPTIONS
    CONFIG = load_config(args.config)
    LANE_OPTIONS = CONFIG["lanes"]

    sources = [s.strip() for s in args.sources.split(",") if s.strip()]
    counter = {"n": 1}
    all_rows = []
    counts = {}

    review_map = {}
    if args.review_map and args.review_map.is_file():
        try:
            review_map = json.loads(
                args.review_map.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            review_map = {}

    if "routing" in sources and args.routing and args.routing.is_file():
        rows, c = extract_routing(args.routing, args.limit,
                                  str(args.routing), counter,
                                  args.goals)
        all_rows.extend(rows)
        counts["routing"] = c
    if "review" in sources and args.reviews and args.reviews.is_dir():
        cb = str(args.cookbooks) if args.cookbooks else None
        rows, c = extract_review(args.reviews, cb, review_map, args.limit,
                                 counter)
        all_rows.extend(rows)
        counts["review"] = c
    if "adr" in sources and args.adr and args.adr.is_dir():
        rows, c = extract_adr(args.adr, args.base, args.model, args.limit,
                              counter)
        all_rows.extend(rows)
        counts["adr"] = c

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        for r in all_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # report
    print("=== extract.py report ===", file=sys.stderr)
    for src in sources:
        c = counts.get(src)
        if c is None:
            print(f"{src}: not run (missing input)", file=sys.stderr)
            continue
        print(f"{src}: read={c.get('read',0)} kept={c.get('kept',0)} "
              f"skipped={len(c.get('skipped',[]))}", file=sys.stderr)
        if src == "routing":
            print(f"  enriched: {c.get('enriched',0)}", file=sys.stderr)
        if src == "adr":
            print(f"  option_leaks: {c.get('option_leaks',0)}", file=sys.stderr)
        for s in c.get("skipped", [])[:10]:
            print(f"  skipped: {s}", file=sys.stderr)
    print(f"total rows written: {len(all_rows)} -> {args.out}",
          file=sys.stderr)


if __name__ == "__main__":
    main()
