# Runbook

The complete ordered commands, mock modes, thresholds and reviewer contract are in [Operating the pipeline](operations.md).

Start offline from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
PYTHONDONTWRITEBYTECODE=1 python3 scripts/demo.py --work-dir .work/demo
```

The repeated-read gate is `scripts/decid3.py`. The old single-read 0.95 exit rule is not shipped as an active CLI. A real endpoint base must end in `/v1`. Default demo completion explicitly reports `AUDIT NOT RUN`.
