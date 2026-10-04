#!/usr/bin/env python3
"""Synthetic OpenAI-compatible mock: clean, seeded noise, or planted code bias."""
import argparse
import hashlib
import json
import math
import random
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ENTITIES = {"Acme Corp": "vendor", "Zephyr": "project", "Orion": "project",
            "robot-7": "bot", "FictionalPerson": "person", "rack-b2": "node"}


def scrub(text):
    entities, counts = [], {}
    for original, cls in ENTITIES.items():
        if re.search(re.escape(original), text, re.I):
            counts[cls] = counts.get(cls, 0) + 1
            placeholder = f"{cls}_{counts[cls]}"
            entities.append({"original": original, "placeholder": placeholder})
            text = re.sub(re.escape(original), placeholder, text, flags=re.I)
    return {"text": text, "entities": entities}


def pick(user, bias=False):
    letters = re.findall(r"^([A-Z])\. ", user, re.M)
    if bias and re.search(r"code_\d+", user):
        return letters[1], letters
    match = re.search(r"Shape: (\w+)|SEV-(MAJOR|MINOR)|(cost)", user)
    feature = next((g for g in (match.groups() if match else ()) if g), "x")
    value = int(hashlib.sha1(feature.encode()).hexdigest(), 16)
    return letters[value % (len(letters) - 1)], letters


def respond(payload, noise=0.0, bias=False, rng=None):
    rng = rng or random.Random(7)
    messages = payload["messages"]
    user = messages[-1]["content"]
    system = messages[0]["content"] if messages[0]["role"] == "system" else ""
    if payload.get("logprobs"):
        if "Yes or No" in system:
            yes = "decided" in user.split("OPTIONS:")[0].lower()
            top = [{"token": "Yes", "logprob": math.log(0.9 if yes else 0.1)},
                   {"token": "No", "logprob": math.log(0.1 if yes else 0.9)}]
        else:
            best, letters = pick(user, bias)
            if rng.random() < noise:
                best = rng.choice([x for x in letters if x != best])
            top = [{"token": best, "logprob": -0.1}] + [
                {"token": x, "logprob": -3.0 - i}
                for i, x in enumerate(x for x in letters if x != best)]
        body = {"choices": [{"message": {"content": top[0]["token"]},
                             "logprobs": {"content": [{"top_logprobs": top}]}}]}
    elif any("RECORD:\n" in m["content"] for m in messages):
        record = next(m["content"].split("RECORD:\n", 1)[1]
                      for m in messages if "RECORD:\n" in m["content"])
        decision = re.search(r"Decision: (.+)", record).group(1).strip()
        alternatives = [x.strip() for x in re.search(r"Alternatives: (.+)", record).group(1).split(";")]
        context = re.search(r"Context: (.+)", record).group(1).strip()
        content = {"context": context, "options": [decision] + alternatives,
                   "label": decision, "alternatives_named": len(alternatives)}
        body = {"choices": [{"message": {"content": json.dumps(content)}}]}
    elif "TEXT:\n" in user:
        body = {"choices": [{"message": {"content": json.dumps(scrub(user.split("TEXT:\n", 1)[1]))}}]}
    else:
        raise ValueError("Unsupported mock request shape")
    return body


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        if self.path != "/v1/chat/completions":
            self.send_error(404)
            return
        payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        body = respond(payload, self.server.noise, self.server.bias, self.server.rng)
        data = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def make_server(port=0, noise=0.0, bias=False, seed=7):
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.noise, server.bias, server.rng = noise, bias, random.Random(seed)
    return server


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("port", type=int)
    ap.add_argument("noise", type=float, nargs="?", default=0.0)
    ap.add_argument("mode", choices=("clean", "bias"), nargs="?", default="clean")
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()
    if not 0 <= a.noise <= 1:
        ap.error("noise must be in [0, 1]")
    with make_server(a.port, a.noise, a.mode == "bias", a.seed) as server:
        print(f"MOCK http://127.0.0.1:{server.server_port}/v1", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
