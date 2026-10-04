#!/usr/bin/env python3
"""decidability.py — measure raw vs scrubbed decision agreement.

For each sampled row id present in both raw and scrubbed files, ask the model
to pick a letter for the same question/state (raw and scrubbed), using
logprobs. Agreement = top letter equal. The repeated-read CLI is decid3.py.
"""
import argparse
import json
import math
import random
import re
import sys
import time
import urllib.error
import urllib.request
from common import open_request
from pathlib import Path

PLACEHOLDER_RE = re.compile(
    r"project_\d+|bot_\d+|persona_\d+|node_\d+|person_\d+|vendor_\d+|"
    r"ref_\d+|id_\d+|month-(?:\d{4}|YYYY)-(?:\d{2}|MM)"
)


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


def chat_logprobs(base, model, system, user, *, timeout=180, retries=2):
    """Return the first token's top_logprobs list of {token, logprob}."""
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0,
        "max_tokens": 2,
        "logprobs": True,
        "top_logprobs": 20,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    last_err = None
    for _ in range(retries):
        try:
            data = _post_json(base, payload, timeout=timeout)
            return data, True
        except (urllib.error.URLError, urllib.error.HTTPError, KeyError,
                ValueError, TimeoutError) as e:
            last_err = e
            time.sleep(2)
    return {"_error": str(last_err)}, False


def first_token_top_logprobs(data):
    """Extract the first generated token's top_logprobs list."""
    try:
        content = data["choices"][0]["logprobs"]["content"]
    except (KeyError, IndexError, TypeError):
        return []
    if not content:
        return []
    first = content[0]
    tlps = first.get("top_logprobs") or []
    out = []
    for item in tlps:
        tok = item.get("token", "")
        lp = item.get("logprob")
        if lp is None:
            continue
        out.append((tok, lp))
    return out


def letter_for(s):
    """Map a token string to an option letter A-Z or None."""
    s = s.strip()
    if not s:
        return None
    c = s[0].upper()
    if "A" <= c <= "Z":
        return c
    return None


def top_letter(top_lps, option_letters):
    """Given top_logprobs and the set of valid option letters, softmax over
    option-letter tokens. Missing letters get min observed logprob - 3.
    Returns the top letter (or None if no option letters present).
    """
    observed = {}  # letter -> logprob (best/first)
    all_lps = []
    for tok, lp in top_lps:
        L = letter_for(tok)
        all_lps.append(lp)
        if L is None:
            continue
        if L in option_letters:
            if L not in observed:
                observed[L] = lp
    if not observed:
        return None
    min_lp = min(all_lps) if all_lps else min(observed.values())
    floor = min_lp - 3
    scores = {}
    for L in option_letters:
        scores[L] = observed.get(L, floor)
    # softmax
    mx = max(scores.values())
    exps = {L: math.exp(scores[L] - mx) for L in scores}
    Z = sum(exps.values())
    probs = {L: exps[L] / Z for L in scores}
    return max(probs, key=probs.get)


def build_user(state, question, options):
    letters = [chr(ord("A") + i) for i in range(len(options))]
    lines = []
    lines.append(state)
    lines.append("")
    lines.append(question)
    for L, opt in zip(letters, options):
        lines.append(f"{L}. {opt}")
    lines.append(f"{chr(ord('A') + len(options))}. None of these; escalate")
    lines.append("Answer with the single letter only.")
    return "\n".join(lines)


def load_jsonl(path):
    out = {}
    if not path or not path.is_file():
        return out
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            rid = obj.get("id")
            if rid:
                out[rid] = obj
    return out


