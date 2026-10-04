# From records to triples

The extraction boundary determines whether a student learns to decide or merely to copy. The private corpus had routing ledger lines, reconciliation-table findings and architecture records. The public examples use only the supplied synthetic records; no real row, example or entity pairing is included.

## Schema and input contracts

`extract.py` emits `id`, `source`, `gate`, `state`, `question`, `options`, `label`, `extra` and `provenance`. `gate` is a class identifier, not a gate verdict. Metadata can contain source paths and outcomes that are deliberately excluded from the decision state. It stays local. The audit sampler projects only its explicit field allowlist and replaces source identifiers with sample-local identifiers.

For ROUTE, one JSONL object supplies `task`, `shape`, `goal`, `declared`, `actual`, `result` and `rework`. The public lane vocabulary and ordered substring rules live in `configs/pipeline.json`. The actual lane becomes the label. Declared lane, result and rework are diagnostic metadata, never state text. This normalizer is intentionally simple; unknown values become `other`.

A task matching `^t\d+[a-z]?$` is looked up in a project task table. Only the `what` cell is copied. Reading its route or status would reveal the outcome. Missing tables leave the identifier in place and mark enrichment as unsuccessful. The original extraction still had 13 such rows because a project file had been archived.

For REVIEW, find an exact APPLY or REJECT cell in each Markdown table row. The immediately preceding cell is the finding; the change cell after the verdict is ignored. Optional file-reference resolution locates up to 3 surrounding lines. This was implemented historically, but those lines were removed later because the current file can already contain the accepted repair. Reproducing extraction is not an endorsement of keeping that context.

For ARCH, read the first 6,000 characters, request `context`, `options`, `label` and `alternatives_named`, parse the first balanced JSON object, and retry once with the prior output plus a valid-JSON instruction on parse failure. Require at least 2 options and a label verbatim in them. The original records supplied 2 to 9 options. Shuffle with a record-text SHA-1-derived seed and carry the label through the permutation.

## Guarded context generation

The prompt requests a 2-4 sentence English situation before the decision: constraints, evidence and competing options, without the chosen outcome. It explicitly forbids decision phrases such as “was adopted” and “rolled back”. The input still contains the decision; this is a guarded summary, not a truly label-blind source.

The overlap filter rejects a context if its longest common substring with the label reaches 25 characters, or if at least 60 % of label tokens of length 3 or more appear in the context. One rewrite request follows; a second leak drops the record. A separate diagnostic logs long verbatim appearances of non-label options. That diagnostic does not establish semantic independence.

Thresholds were chosen once and never calibrated. The first prompt kept all 157 records, but round 1 found 10 leaks among 17 audited ARCH rows. The guarded version kept 131 and dropped 26, yet the later semantic filter removed 92 of 124 mechanically usable rows. The layers detect different things.

## Procedure and interpretation

The original extraction read sources without modifying them. After the first audit, ARCH was re-extracted with the guarded prompt and filter. ROUTE descriptions were back-filled separately. The source records were mixed-language; ARCH context is translated/generated paraphrase, not a quotation.

Run the synthetic extraction through `scripts/demo.py`, or use the explicit commands in [operations](operations.md). Tests assert the schema, source counts, label membership, task-table enrichment and exclusion of the change column. They do not validate a real model's paraphrase fidelity.

See [the complete extraction tables](results.md#extraction-results), dated 2026-09-22, for every count and audit condition.

**Rule:** separate state construction from outcome access wherever possible, document remaining exposure, and do not infer leak recall from a clean syntactic filter.
