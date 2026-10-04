"""Configuration and strict mechanical checks for the public adapters."""
import json
import io
import os
import random
import re
import urllib.request
from urllib.parse import urlsplit
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_MOCK_RNG = random.Random(7)


def open_request(request, timeout=180):
    """Explicit synthetic test transport; normal mode uses the supplied endpoint."""
    mode = os.environ.get("COOKBOOK_MOCK_MODE")
    if mode:
        if mode not in ("clean", "bias", "noise"):
            raise ValueError("Unknown synthetic mock mode")
        if urlsplit(request.full_url).path != "/v1/chat/completions":
            raise ValueError("Mock endpoint requires /v1/chat/completions")
        from mock_server import respond
        payload = json.loads(request.data)
        response = respond(payload, noise=0.25 if mode == "noise" else 0.0,
                           bias=mode == "bias", rng=_MOCK_RNG)
        return io.BytesIO(json.dumps(response).encode())
    return urllib.request.urlopen(request, timeout=timeout)


def load_config(path=None):
    return json.loads(Path(path or ROOT / "configs/pipeline.json").read_text())


def load_patterns(path):
    if path is None:
        raise ValueError("A nonempty patterns file is required")
    patterns = []
    for line in Path(path).read_text().splitlines():
        if line.strip() and not line.lstrip().startswith("#"):
            patterns.append(re.compile(line.strip(), re.I))
    if not patterns:
        raise ValueError("A nonempty patterns file is required")
    return patterns


def read_rows(path):
    rows = [json.loads(line) for line in Path(path).read_text().splitlines()
            if line.strip()]
    ids = [row["id"] for row in rows]
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate row identifiers")
    return rows


def write_rows(path, rows):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with Path(path).open("w") as output:
        for row in rows:
            output.write(json.dumps(row, ensure_ascii=True) + "\n")


def strip_context(state):
    return re.sub(r"\n\s*Context:.*\Z", "", state, flags=re.S)
