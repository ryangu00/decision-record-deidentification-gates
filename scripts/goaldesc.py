#!/usr/bin/env python3
"""Generic description experiment. Only its validator is supported by the mock."""
import argparse
import json
import re
import urllib.request
from common import open_request

from common import load_config, load_patterns, read_rows

PROMPT = (
    "Given an engineering project slug and task lines, write a generic description "
    "in 3 to 10 English words, such as 'log storage migration' or 'GPU inference "
    "stack benchmark'. No names, dates, numbers, routing lanes or who should do "
    "the work. Output only the description.\n\n"
)


def valid(description, patterns, tokens, lane_pattern):
    if not description or len(description.split()) > 12 or "\n" in description:
        return "shape"
    if re.search(r"\b(19|20)\d\d\b", description):
        return "year"
    if re.search(lane_pattern, description, re.I):
        return "lane"
    if any(p.search(description) for p in patterns):
        return "mechanical"
    if any(t.lower() in description.lower() for t in tokens):
        return "token"
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for flag in ("raw", "out", "patterns", "tokens"):
        ap.add_argument("--" + flag, required=True)
    ap.add_argument("--config")
    ap.add_argument("--base", default="http://127.0.0.1:8000/v1")
    ap.add_argument("--model", default="local-model")
    a = ap.parse_args()
    config = load_config(a.config)
    patterns = load_patterns(a.patterns)
    with open(a.tokens) as stream:
        tokens = [line.split("\t")[0] for line in stream
                  if line.strip() and not line.startswith("#")]
    goals = {}
    for row in read_rows(a.raw):
        match = re.search(r"^Goal: (.+?)\s*$", row["state"], re.M)
        if row["gate"] == "ROUTE" and match:
            context = " | ".join(re.findall(r"^(?:Task|Shape): (.+?)\s*$", row["state"], re.M))
            goals.setdefault(match.group(1), []).append(context)
    descriptions, rejected = {}, {}
    for slug, lines in goals.items():
        payload = {"model": a.model, "temperature": 0, "max_tokens": 40,
                   "chat_template_kwargs": {"enable_thinking": False},
                   "messages": [{"role": "user", "content": PROMPT + "Slug: " + slug
                                 + "\nTask lines:\n" + "\n".join(lines[:6])}]}
        request = urllib.request.Request(a.base.rstrip("/") + "/chat/completions",
                                         data=json.dumps(payload).encode(),
                                         headers={"Content-Type": "application/json"})
        try:
            with open_request(request, timeout=120) as response:
                desc = json.load(response)["choices"][0]["message"]["content"].strip().strip('"').strip(".").strip()
            reason = valid(desc, patterns, tokens, config["lane_words"])
            if reason:
                rejected[slug] = reason
            else:
                descriptions[slug] = desc
        except Exception:
            rejected[slug] = "model_error"
    with open(a.out, "w") as output:
        json.dump({"desc": descriptions, "rejected": rejected}, output, indent=2)
    print(f"goals {len(goals)} described {len(descriptions)} rejected {len(rejected)}")


if __name__ == "__main__":
    main()
