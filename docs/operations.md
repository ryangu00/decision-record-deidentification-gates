# Operating the pipeline

The final protocol is extract -> model scrub -> map cleanup -> deterministic repairs and mechanical rescan -> semantic label-leak filter -> decidability -> independent audit. Any upstream change invalidates every downstream gate result. The original process did not follow that rule between versions 2 and 4 for ROUTE and REVIEW.

## Offline prerequisites and boundaries

The synthetic path uses Python 3 and its standard library. It installs nothing, fetches no weights, uses no credential and contacts no hosted model. The source scripts were checked on Python 3.14.6; a minimum supported Python version was not established.

Fixtures are invented. Acme Corp, Zephyr, Orion, robot-7, rack-b2 and FictionalPerson are synthetic entity tokens, not real names drawn from a record. The synthetic severity convention is SEV-MAJOR/SEV-MINOR. Raw fixture dates, counts and record identifiers belong only to the supplied test data.

Run from the repository root. The runner requires a new work directory and writes a local `.gitignore` there. Raw rows, maps, codes, per-row diagnostics and samples remain working data. Nothing in the scripts publishes them. When replacing fixtures with private inputs, keep that whole directory private as well.

## Start with the fixture and tests

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
PYTHONDONTWRITEBYTECODE=1 python3 scripts/demo.py --work-dir .work/demo
```

The demo runs the same request-building code through an explicitly selected in-process synthetic transport. It starts no listener and needs no network. Its final message is `PIPELINE COMPLETE; AUDIT NOT RUN`.

Inspect `.work/demo/pipeline.log`, `.work/demo/gate-summary.json` and `.work/demo/audit.txt` locally. The fact sheet's clean-fixture expectations are 84 extracted/passing rows, 6 enriched tasks, 6 map entities, 76 changed rows in deterministic repair, 12 distinct codes and no semantic drops. The source's gate example sampled 30 per class; the consolidated runner instead uses its final-run cap of 200, so it reads every synthetic row.

`gate-summary.json` includes raw/scrubbed marginals, chance agreement, both floor estimators, stability strata and the selected gate mode. A clean synthetic result tests control flow and contracts, not real anonymization quality. The audit pre-check being clear is not an independent reviewer verdict.

## Stage-by-stage commands

These commands use the supplied synthetic inputs. Use a fresh directory, keep the map local and do not print it.

```sh
mkdir -p .work/manual
printf '*\n' > .work/manual/.gitignore
export PYTHONDONTWRITEBYTECODE=1
export COOKBOOK_MOCK_MODE=clean
python3 scripts/extract.py \
  --routing fixtures/routing.jsonl --reviews fixtures/reviews \
  --adr fixtures/adr --goals fixtures/goals \
  --config configs/pipeline.json --out .work/manual/raw.jsonl
python3 scripts/scrub.py --in .work/manual/raw.jsonl \
  --out .work/manual/model-scrubbed.jsonl --map .work/manual/map.json \
  --patterns configs/patterns.example.txt --config configs/pipeline.json
python3 scripts/mapclean.py --map .work/manual/map.json \
  --in .work/manual/model-scrubbed.jsonl --out .work/manual/map-repaired.jsonl \
  --map-out .work/manual/map-clean.json --keep configs/keep.example.txt
python3 scripts/postscrub2.py --in .work/manual/map-repaired.jsonl \
  --raw .work/manual/raw.jsonl --out .work/manual/repaired.jsonl \
  --map .work/manual/map-clean.json --codes .work/manual/codes.json \
  --config configs/pipeline.json
python3 scripts/postscrub.py --in .work/manual/repaired.jsonl \
  --out .work/manual/mechanical.jsonl --map .work/manual/map-clean.json \
  --patterns configs/patterns.example.txt --tokens configs/tokens.example.tsv \
  --config configs/pipeline.json
python3 scripts/leakcheck.py --in .work/manual/mechanical.jsonl \
  --out .work/manual/usable.jsonl --dropped .work/manual/dropped.jsonl \
  --config configs/pipeline.json
python3 scripts/decid3.py --raw .work/manual/raw.jsonl \
  --scrubbed .work/manual/usable.jsonl --per-gate 30 --reps 3 \
  --scrubbed-options --stability-report --floor-estimator mean-pairs \
  --out .work/manual/reads.jsonl --summary .work/manual/gate-summary.json
python3 scripts/sample.py --in .work/manual/usable.jsonl \
  --out .work/manual/sample50.jsonl
sh scripts/review_runner.sh --prompt configs/p-audit-scrub-v2.txt \
  --sample .work/manual/sample50.jsonl --patterns configs/patterns.example.txt \
  --out .work/manual/audit.txt
```

The synthetic review table has no resolved file context, so the manual raw comparison above needs no stripping. With real resolved contexts, remove the same REVIEW context on the raw side before calling the gate. `run_pipeline.py` performs that normalization into `raw-no-context.jsonl` automatically.

Historical repairs accumulated over multiple rounds, with some post-processing after the semantic check. The consolidated runner places deterministic repairs before a final mechanical rescan and semantic check, ensuring every changed field is checked downstream. Historical counts are not rerun results from this new order.

## Mock modes

`COOKBOOK_MOCK_MODE` is an explicit test switch. Omit it for an actual HTTP endpoint. Accepted values are `clean`, `bias` and `noise`. Unknown values fail. The mock supports extraction JSON, scrub JSON and first-token logprobs; it rejects the separate generic-description generation request.

Clean mode derives a letter from content words that survive scrubbing: task shape, severity or cost. Bias mode forces option B when a `code_N` token appears. Noise mode independently flips reads with probability 0.25 using a seeded generator. This is a synthetic mechanism, not a model of the production endpoint's unidentified jitter.

```sh
COOKBOOK_MOCK_MODE=bias python3 scripts/decid3.py \
  --raw .work/demo/raw-no-context.jsonl --scrubbed .work/demo/usable.jsonl \
  --per-gate 30 --reps 3 --scrubbed-options \
  --out .work/demo/bias-neutral-reads.jsonl
COOKBOOK_MOCK_MODE=noise python3 scripts/decid3.py \
  --raw .work/demo/raw-no-context.jsonl --scrubbed .work/demo/usable.jsonl \
  --per-gate 30 --reps 3 --stability-report --floor-estimator mean-pairs \
  --out .work/demo/noisy-reads.jsonl
```

Noise may produce a failing class even with unchanged semantics. Exit 2 is a gate result, not a shell malfunction. Tests plant both state-level and option-only bias and verify that the gate distinguishes them.

For an actual loopback HTTP exercise on a machine that permits socket binding:

```sh
python3 scripts/demo.py --http --work-dir .work/http-demo
```

Or start the standalone server with `python3 scripts/mock_server.py 0 0.25 bias --seed 23`. Port 0 requests an available port from the OS; use the printed `/v1` base. A nonzero occupied port fails to bind. The authoring environment rejected loopback binding, so listener/socket handling was not validated there. The in-process mock does not substitute for that HTTP verification.

## Parameterized runner and audit adapter

`sh scripts/run_gates.sh --work-dir .work/another-run` runs the same ordered stages. Set `COOKBOOK_MOCK_MODE=clean` for the socket-free path, or pass `--base` and `--model` for a local server after unsetting the test switch. A base must include `/v1`; clients append `/chat/completions`.

The runner takes `--fixtures`, `--configs`, `--work-dir`, `--base`, `--model` and an optional trailing `--reviewer` command. The standalone wrapper accepts trailing `--command` in the same manner. The command receives `prompt.txt` and `sample50.jsonl` as its final arguments in a staging directory containing only the scanned inputs.

Supply read-only sandbox enforcement in that command. The wrapper performs content checks, projection/staging and response validation; it does not create an OS sandbox. Credential setup, service-specific CLI details and permission policy for a real reviewer are deliberately unspecified. They cannot be inferred from the fact sheet.

With no reviewer command the wrapper runs a local pre-check and explicitly records NOT RUN. With a no-op command it rejects the empty response instead of declaring CLEAN. Tests use only local no-op behavior, never a hosted review. Both the prompt and the sample must pass the pattern file before any command invocation.

## Ablation and optional descriptions

```sh
python3 scripts/ablate.py --raw .work/demo/raw-no-context.jsonl \
  --scrubbed .work/demo/usable.jsonl --out-dir .work/demo/ablation
```

This writes the three field-isolation variants. Feed each to `decid3.py` against the same raw file to compare transformations. The synthetic fixture has no real project-identity signal, so do not expect the private ablation's numerical outcomes.

`goaldesc.py` retains the description client and configurable validator. The mock does not implement description generation, and only the validator is tested. This is distinct from the proposed structured ROUTE re-extraction, which was not done and is not implemented here.

## Thresholds and reruns

| Check | Acceptance in this implementation |
|---|---|
| Mechanical | Usable rows and outbound payloads have no configured pattern hit; missing/malformed rule file fails |
| Semantic label leaks | Median p(yes) below 0.5 on 3 complete reads for free-text options |
| Decidability | Agreement >= selected raw floor - 0.05; no empty comparison or incomplete read |
| Audit | Explicit independent verdict under the final written rule; a pre-check alone is NOT RUN |

A failed row is excluded, not silently repaired into acceptance. A failed gate command stops the runner before sampling or external review. Restart into a new work directory to avoid mistaking stale results for current evidence.

The original timeline took 2 h 31 min from first scrub to final ablation; the detailed [timeline and cost table](results.md#timeline-and-cost) is historical. No comparable production timing is claimed for this offline demo. Long real extraction should write a local log and run detached from short-lived foreground tool limits.
