#!/usr/bin/env python3
"""Parameterized offline runner replacing the private round-specific wrappers."""
import argparse
import datetime
import shutil
import subprocess
import sys
from pathlib import Path

from common import ROOT, read_rows, strip_context, write_rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fixtures", type=Path, default=ROOT / "fixtures")
    ap.add_argument("--configs", type=Path, default=ROOT / "configs")
    ap.add_argument("--work-dir", type=Path, required=True)
    ap.add_argument("--base", default="http://127.0.0.1:8000/v1")
    ap.add_argument("--model", default="local-model")
    ap.add_argument("--reviewer", nargs=argparse.REMAINDER)
    a = ap.parse_args(argv)
    work = a.work_dir.resolve()
    work.mkdir(parents=True, exist_ok=False)
    (work / ".gitignore").write_text("*\n")
    config = a.configs.resolve()
    fixture = a.fixtures.resolve()
    endpoint = ["--base", a.base, "--model", a.model]
    rules = ["--config", str(config / "pipeline.json")]
    patterns = ["--patterns", str(config / "patterns.example.txt")]

    def run(script, *args):
        command = [sys.executable, str(ROOT / "scripts" / script), *map(str, args)]
        with (work / "pipeline.log").open("a") as log:
            log.write(datetime.datetime.now().isoformat() + " " + script + "\n")
            log.flush()
            result = subprocess.run(command, stdout=log, stderr=log, check=False)
        if result.returncode:
            raise subprocess.CalledProcessError(result.returncode, script)
        print("COMPLETED " + script, flush=True)

    run("extract.py", "--routing", fixture / "routing.jsonl", "--reviews", fixture / "reviews",
        "--adr", fixture / "adr", "--goals", fixture / "goals", "--out", work / "raw.jsonl",
        *endpoint, *rules)
    run("scrub.py", "--in", work / "raw.jsonl", "--out", work / "model-scrubbed.jsonl",
        "--map", work / "map.json", *patterns, *endpoint, *rules)
    run("mapclean.py", "--map", work / "map.json", "--in", work / "model-scrubbed.jsonl",
        "--out", work / "map-repaired.jsonl", "--map-out", work / "map-clean.json",
        "--keep", config / "keep.example.txt")
    run("postscrub2.py", "--in", work / "map-repaired.jsonl", "--raw", work / "raw.jsonl",
        "--out", work / "repaired.jsonl", "--map", work / "map-clean.json",
        "--codes", work / "codes.json", *rules)
    run("postscrub.py", "--in", work / "repaired.jsonl", "--out", work / "mechanical.jsonl",
        "--map", work / "map-clean.json", "--tokens", config / "tokens.example.tsv", *patterns, *rules)
    run("leakcheck.py", "--in", work / "mechanical.jsonl", "--out", work / "usable.jsonl",
        "--dropped", work / "dropped.jsonl", *endpoint, *rules)
    raw = read_rows(work / "raw.jsonl")
    for row in raw:
        if row["gate"] == "REVIEW":
            row["state"] = strip_context(row["state"])
    write_rows(work / "raw-no-context.jsonl", raw)
    run("decid3.py", "--raw", work / "raw-no-context.jsonl", "--scrubbed", work / "usable.jsonl",
        "--out", work / "reads.jsonl", "--summary", work / "gate-summary.json", "--per-gate", 200,
        "--reps", 3, "--scrubbed-options", "--stability-report", "--floor-estimator", "mean-pairs", *endpoint)
    run("sample.py", "--in", work / "usable.jsonl", "--out", work / "sample50.jsonl")
    command = ["--command", *a.reviewer] if a.reviewer else []
    run("review_runner.py", "--prompt", config / "p-audit-scrub-v2.txt", "--sample", work / "sample50.jsonl",
        "--out", work / "audit.txt", *patterns, *command)
    print("PIPELINE COMPLETE; " + ("reviewer ran" if a.reviewer else "AUDIT NOT RUN"))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as error:
        print(f"PIPELINE STOPPED: {error.cmd} exit={error.returncode}", file=sys.stderr)
        raise SystemExit(error.returncode)
