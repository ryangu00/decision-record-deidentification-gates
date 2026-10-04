#!/usr/bin/env python3
"""scrub.py — de-identify decision triples behind two fail-closed gates.

Model rewrite: model rewrites state, replacing private entities with
stable placeholders, using/merging an entity->placeholder map.
Mechanical gate: any regex from --patterns matching a decision field
fails the row (written with scrub_failed=true).
"""
import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from common import open_request
from pathlib import Path


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
            time.sleep(2)
    return (f"MODEL_ERROR: {last_err}", False)


def first_json_block(text):
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
    text, ok = chat(base, model, messages, max_tokens=max_tokens,
                    timeout=timeout)
    if not ok:
        return None, text, False
    obj = first_json_block(text)
    if obj is not None:
        return obj, text, True
    retry = messages + [
        {"role": "assistant", "content": text},
        {"role": "user",
         "content": "return only valid JSON (a single object, nothing else)"},
    ]
    text2, ok2 = chat(base, model, retry, max_tokens=max_tokens,
                      timeout=timeout)
    if not ok2:
        return None, text2, False
    obj2 = first_json_block(text2)
    if obj2 is not None:
        return obj2, text2, True
    return None, text2, False


SCRUB_INSTRUCTION = (
    "Rewrite the text so that every project name, code name, agent or bot "
    "name, persona name, machine or host name, people, private vendor and exact date becomes a "
    "stable placeholder. Use these placeholder classes: project_N, bot_N, "
    "persona_N, node_N, person_N, vendor_N, month-YYYY-MM, id_N. The id_N "
    "class covers opaque identifiers: hex ids, tokens, hashes, account or "
    "environment ids, API keys and any other non-public machine-generated "
    "identifier string. Keep all "
    "technical content, numbers, public product and library names, and the "
    "decision-relevant meaning unchanged. Reply with JSON "
    '{"text": "<rewritten>", "entities": '
    '[{"original": "...", "placeholder": "..."}]}'
    " Do NOT replace generic engineering or process vocabulary (for example: handshake, review, gate, audit, fresh-context, rollback, deploy, benchmark), public tool, library, vendor or model names (for example vLLM, Docker, NVIDIA, Qwen, Postgres), or technical measurements. Only private identifiers become placeholders."
)

CLASS_RE = re.compile(
    r"^(project|bot|persona|node|person|vendor|id)_(\d+)$|^month-(\d{4}-\d{2})$"
)


def next_in_class(class_name, existing_map):
    """Return next placeholder string for a class (first-come numbering)."""
    used = set()
    for ph in existing_map.values():
        m = CLASS_RE.match(ph)
        if not m:
            continue
        if m.group(1) == class_name:
            used.add(int(m.group(2)))
    n = 1
    while n in used:
        n += 1
    if class_name == "month":
        # month placeholders are date-shaped; caller passes exact
        return None
    return f"{class_name}_{n}"


def apply_map_longest_first(text, ent_map):
    if not ent_map:
        return text
    # longest original first
    items = sorted(ent_map.items(), key=lambda kv: len(kv[0]),
                   reverse=True)
    out = text
    # Historical substring replacement: no word boundary.
    # Poisoned map keys can re-replace placeholders; mapclean is required.
    for orig, ph in items:
        if orig and orig in out:
            out = out.replace(orig, ph)
    return out


def classify_placeholder(ph):
    m = CLASS_RE.match(ph)
    if not m:
        return None
    if m.group(1):
        return m.group(1)
    return "month"


def merge_entities(new_entities, ent_map):
    """Merge model-returned entities into the map (first-come per class).

    Returns merged map and the mapping used for THIS call (original->ph)
    so we can rewrite the model's text consistently.
    """
    # first, apply existing map to dedupe originals already mapped
    added = dict(ent_map)
    for ent in new_entities:
        orig = ent.get("original")
        ph = ent.get("placeholder")
        if not orig or not ph:
            continue
        if orig in added:
            continue  # already mapped, keep stable
        cls = classify_placeholder(ph)
        # month placeholders keep their date value as-is (stable by date)
        if cls == "month":
            if ph not in [v for v in added.values()
                          if v.startswith("month-")]:
                added[orig] = ph
            elif orig not in added:
                # find existing month ph for this date
                added[orig] = ph
            continue
        if cls is None:
            # unknown shape: still record verbatim (first-come-ish)
            added[orig] = ph
            continue
        # assign next-in-class so numbering is contiguous & stable
        next_ph = next_in_class(cls, added)
        added[orig] = next_ph
    return added


def rewrite_consistent(model_text, model_entities, ent_map_new):
    """After merging, the model may have used placeholder numbering that
    differs from the map's first-come numbering. Re-apply the new map so the
    final text uses canonical placeholders. We map model placeholders -> map
    placeholders via the original strings.
    """
    # Build model_ph -> original -> map_ph
    # For each entity the model returned, its original may map (in new map)
    # to a possibly different placeholder. Replace model ph with map ph.
    out = model_text
    repls = []
    for ent in model_entities:
        orig = ent.get("original")
        mph = ent.get("placeholder")
        if not orig or not mph:
            continue
        map_ph = ent_map_new.get(orig, mph)
        if mph != map_ph:
            repls.append((mph, map_ph))
    # longest first to avoid substring clobber
    repls.sort(key=lambda kv: len(kv[0]), reverse=True)
    for mph, map_ph in repls:
        out = out.replace(mph, map_ph)
    return out


def load_map(path):
    if path and path.is_file():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def save_map(path, m):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(m, ensure_ascii=False, indent=2,
                               sort_keys=True) + "\n", encoding="utf-8")


from common import load_config
OPTION_VOCAB = frozenset(load_config()["lanes"] + ["APPLY", "REJECT"])


def options_are_free_text(options):
    """True unless every option string is in the fixed vocabulary set."""
    if not options:
        return False
    return any(opt not in OPTION_VOCAB for opt in options)


def scrub_text(base, model, text, ent_map, *, max_tokens=900, timeout=180):
    """Run the model rewrite on a single string using/merging ent_map.

    Returns (rewritten, new_map, ok). On model/parse failure ok is False and
    rewritten is the raw input text (fail-closed upstream). ent_map is mutated
    in place when ok.
    """
    pre = apply_map_longest_first(text, ent_map)
    obj, raw, ok = chat_json(
        base, model,
        [{"role": "user",
          "content": SCRUB_INSTRUCTION + "\n\nTEXT:\n" + pre}],
        max_tokens=max_tokens,
        timeout=timeout,
    )
    if not ok or obj is None:
        return text, ent_map, False, raw
    ents = obj.get("entities", []) or []
    ent_map.update(merge_entities(ents, ent_map))
    # merge_entities returns a new dict; keep caller's reference stable
    rewritten = rewrite_consistent(obj.get("text", ""), ents, ent_map)
    return rewritten, ent_map, True, raw


from common import load_patterns


def main(argv=None):
    ap = argparse.ArgumentParser(description="Scrub decision triples.")
    ap.add_argument("--in", dest="infile", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--map", dest="mapfile", type=Path, required=True)
    ap.add_argument("--patterns", type=Path, required=True)
    ap.add_argument("--limit", type=int, default=10**9)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--sample-check", type=int, default=0)
    ap.add_argument("--base", default="http://127.0.0.1:8000/v1")
    ap.add_argument("--model", default="local-model")
    ap.add_argument("--config", type=Path)
    args = ap.parse_args(argv)
    global OPTION_VOCAB
    OPTION_VOCAB = frozenset(load_config(args.config)["lanes"] + ["APPLY", "REJECT"])

    patterns = load_patterns(args.patterns)
    ent_map = load_map(args.mapfile)

    rows = []
    with open(args.infile, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
            if len(rows) >= args.limit:
                break

    passed = 0
    failed_by_pattern = {}
    model_failures = 0
    options_scrubbed = 0
    label_not_in_options = 0
    out_rows = []

    if args.dry_run:
        print("=== dry-run: first 5 rows ===", file=sys.stderr)
        for r in rows[:5]:
            state = r.get("state", "")
            # dry-run never persists; scrub against a per-row copy so the
            # on-disk map is untouched and rows stay independent (matches
            # prior dry-run semantics).
            row_map = dict(ent_map)
            rewritten, row_map, ok, raw = scrub_text(
                args.base, args.model, state, row_map)
            if not ok:
                model_failures += 1
                print(f"  {r.get('id')}: MODEL FAILURE {raw[:60]}",
                      file=sys.stderr)
                continue
            options = r.get("options", []) or []
            free = options_are_free_text(options)
            print(f"  {r.get('id')}:", file=sys.stderr)
            print("    state rewrite completed (text suppressed)", file=sys.stderr)
            if free:
                scrubbed_opts = []
                for opt in options:
                    so, row_map, ok_o, _ = scrub_text(
                        args.base, args.model, opt, row_map)
                    scrubbed_opts.append(so if ok_o else opt)
                print(f"    options (free-text, scrubbed):",
                      file=sys.stderr)
                for orig, so in zip(options, scrubbed_opts):
                    print("      option rewrite completed (text suppressed)", file=sys.stderr)
            else:
                print(f"    options (in-vocab, not scrubbed)",
                      file=sys.stderr)
            # do NOT persist map or write out in dry-run
        # counts in dry-run are illustrative only
        print(f"dry-run rows shown: {min(5, len(rows))}; "
              f"model_failures={model_failures}; wrote nothing",
              file=sys.stderr)
        return

    for r in rows:
        state = r.get("state", "")
        rewritten, ent_map, ok, raw = scrub_text(
            args.base, args.model, state, ent_map)
        if not ok:
            model_failures += 1
            # fail-closed: cannot scrub state -> mark failed
            r2 = dict(r)
            r2["state"] = state
            r2["scrub_failed"] = True
            r2["scrub_error"] = "model_or_parse_failure"
            out_rows.append(r2)
            continue
        r2 = dict(r)
        r2["state"] = rewritten
        options = r.get("options", []) or []
        label = r.get("label", "")
        free = options_are_free_text(options)
        # Combined text that mechanical gate must clear: scrubbed state plus, for
        # free-text rows, every scrubbed option and the scrubbed label.
        combined_parts = [rewritten, *options, label] if not free else [rewritten]
        if free:
            options_scrubbed += 1
            scrubbed_opts = []
            option_failed = False
            for opt in options:
                so, ent_map, ok_o, _ = scrub_text(
                    args.base, args.model, opt, ent_map)
                scrubbed_opts.append(so if ok_o else opt)
                option_failed |= not ok_o
            if option_failed:
                model_failures += 1
                r2["scrub_failed"] = True
                r2["scrub_error"] = "option_model_failure"
                out_rows.append(r2)
                continue
            r2["options"] = scrubbed_opts
            # label must equal one raw option; carry over that option's
            # scrubbed text. If it does not, fail the row but keep going.
            try:
                label_idx = options.index(label)
            except ValueError:
                label_idx = None
            if label_idx is None:
                label_not_in_options += 1
                r2["scrub_failed"] = True
                r2["scrub_error"] = "label_not_in_options"
                # leave label as-is (raw) so the failure is auditable
                out_rows.append(r2)
                continue
            label_out = scrubbed_opts[label_idx]
            r2["label"] = label_out
            combined_parts.extend(scrubbed_opts)
            combined_parts.append(label_out)
        combined = "\n".join(combined_parts)
        # mechanical gate: mechanical regex check over the combined scrubbed text
        matched = None
        for idx, p in enumerate(patterns):
            if p.search(combined):
                matched = idx
                break
        if matched is not None:
            r2["scrub_failed"] = True
            r2["failed_pattern"] = matched
            failed_by_pattern[matched] = failed_by_pattern.get(matched, 0) + 1
        else:
            r2["scrubbed"] = True
            passed += 1
        out_rows.append(r2)

    # persist map (never print)
    save_map(args.mapfile, ent_map)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        for r in out_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # optional sample check: re-test a few passing rows
    if args.sample_check:
        sample = [r for r in out_rows if r.get("scrubbed")][:args.sample_check]
        for r in sample:
            blobs = [r.get("state", "")]
            if r.get("options"):
                blobs.extend(r.get("options", []))
            blobs.append(r.get("label", ""))
            combined = "\n".join(blobs)
            for idx, p in enumerate(patterns):
                if p.search(combined):
                    print(f"SAMPLE-CHECK leak: {r.get('id')} pat={idx}",
                          file=sys.stderr)

    print("=== scrub.py report ===", file=sys.stderr)
    print(f"rows: {len(rows)}", file=sys.stderr)
    print(f"passed mechanical gate: {passed}", file=sys.stderr)
    print(f"failed mechanical gate (by pattern index): "
          f"{dict(sorted(failed_by_pattern.items()))}", file=sys.stderr)
    print(f"model failures: {model_failures}", file=sys.stderr)
    print(f"options scrubbed (free-text rows): {options_scrubbed}",
          file=sys.stderr)
    print(f"label_not_in_options failures: {label_not_in_options}",
          file=sys.stderr)
    print(f"map entities: {len(ent_map)} (local-only)", file=sys.stderr)


if __name__ == "__main__":
    main()
