#!/usr/bin/env python3
"""Scan prompt AND sample before an optional user-supplied reviewer command.

The command receives prompt.txt and sample50.jsonl as its final arguments.
Its working directory contains only those input files. Read-only sandboxing
must be provided by that command; this wrapper does not enforce an OS sandbox.
"""
import argparse
import re
import subprocess
import tempfile
from pathlib import Path

from common import load_patterns


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--prompt", type=Path, required=True)
    ap.add_argument("--sample", type=Path, required=True)
    ap.add_argument("--patterns", required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--command", nargs=argparse.REMAINDER)
    a = ap.parse_args(argv)
    patterns = load_patterns(a.patterns)
    texts = {"prompt": a.prompt.read_text(), "sample": a.sample.read_text()}
    for role, text in texts.items():
        if any(pattern.search(text) for pattern in patterns):
            print(f"EGRESS BLOCKED: {role} matched a pattern (content suppressed)")
            return 9
    a.out.parent.mkdir(parents=True, exist_ok=True)
    if not a.command:
        a.out.write_text("AUDIT: NOT RUN (offline pre-check only)\n")
        print("EGRESS PRE-CHECK PASS: prompt and sample; AUDIT NOT RUN")
        return 0
    with tempfile.TemporaryDirectory(prefix="review-", dir=a.out.parent) as stage:
        work = Path(stage)
        (work / "prompt.txt").write_text(texts["prompt"])
        (work / "sample50.jsonl").write_text(texts["sample"])
        with a.out.open("w") as output:
            result = subprocess.run(a.command + ["prompt.txt", "sample50.jsonl"],
                                    cwd=work, stdout=output, stderr=subprocess.PIPE,
                                    text=True, check=False)
    if result.returncode:
        print("AUDIT COMMAND FAILED (stderr suppressed)")
        return result.returncode
    lines = a.out.read_text().strip().splitlines()
    last = lines[-1] if lines else ""
    if last == "AUDIT: CLEAN":
        print(last)
        return 0
    if re.fullmatch(r"AUDIT: LEAKS \(\d+\)", last):
        print(last)
    else:
        print("AUDIT: INVALID RESPONSE")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
