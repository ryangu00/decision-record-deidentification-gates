# Public adaptation and validation boundaries

This repository adapts the supplied scripts rather than claiming to replay the private runs. Historical measurements are confined to their original conditions in [results](results.md). Source records, private maps/configuration, audit samples, raw reviewer tables and earlier dataset versions are not shipped.

## What changed for publication

| Component | Adaptation |
|---|---|
| Extraction | Generic ROUTE/REVIEW class names; lane vocabulary and substring rules in JSON; loopback /v1 default; generic model placeholder |
| Scrubbing | Generic vocabulary config; neutral instruction about people; case-insensitive all-field scan; dry-run text suppressed |
| Map repair | Raw docstring to avoid the recorded escape warning; private entry logging removed; user-supplied keep-list |
| Mechanical post-pass | Configurable whole-Goal regex; strict shared pattern loading |
| Deterministic repairs | Code, alias, named-entity and severity rules moved to synthetic config; punctuation-separated alignment for severity tags |
| Semantic filter | Generic vocabulary and endpoint/model; complete-read requirement; failed rows excluded; stable softmax arithmetic |
| Description step | Synthetic engineering prompt examples and configurable lane exclusions; validator importable for offline tests |
| Readout helpers | Historical single-read threshold CLI removed; repeated-read gate is the supported entry point |
| Decidability | Optional delivered options, stability strata and mean-of-three-pairs floor; ref_N/id_N attribution; marginals and chance agreement |
| Orchestration | Parameterized ordered runner and separate sampler/ablation builder; no service-manager calls or private review command |
| Review runner | Both prompt and sample scanned; generic optional command; no-op response rejected; read-only sandbox delegated to supplied command |
| Mock | FictionalPerson replaces the person token; synthetic matching case-insensitive; seeded clean/noise/bias response code shared by in-process and HTTP paths |

## Additions after the original runs

The three decidability improvements are implemented after the original runs and tested against the mock. None alters the provenance of the published convergence sequence. The default standalone gate retains raw options and a single-pair floor; the runner opts into the improvements explicitly.

The adapter also rejects empty comparison sets, missing raw counterparts, duplicate row identifiers, mismatched/duplicate options and missing readouts. Pattern files must exist, compile and contain a rule. Option-rewrite failure cannot preserve an unsanitized option as a passing row. Semantic-read failure cannot be interpreted as a negative leak judgment. These are code-level fail-closed additions, not measured changes to the historical dataset.

The scrubber still uses plain substring replacement and a permissive merge before map cleanup. The cleanup and later gates are required; the code does not claim to solve all map-collision cases. Exact option ordering is a caller contract; equal counts alone cannot verify arbitrary semantic reordering.

The sampler has a fixed balanced target and fills undersized fixture strata with unused usable rows. It emits actual counts, rather than pretending the fixture has the historical audit composition. Work directories contain their own ignore file so the supplied root ignore template can remain unchanged.

## Tests and their limits

The unittest suite runs the full synthetic pipeline using request objects and the mock JSON contracts without sockets. It covers extraction counts and label membership, task enrichment, excluded outcome columns, map reversal, severity restoration, case-insensitive all-field patterns, invalid pattern files, credential-shape regexes, semantic drops, gate improvements, clean/noisy/biased behavior, sample projection, egress rejection before command invocation and a no-op reviewer.

Tests assert the recorded clean fixture counts. They do not claim to reproduce private historical agreement rates. The mock's decision function is deliberately simple; even a perfect mock agreement can have a degenerate chance baseline. It is a wiring test, not an evaluation model.

The HTTP listener could not bind in the authoring sandbox. Socket-level serving remains unverified there. The in-process transport uses the same response function but does not exercise real HTTP transport, remote authentication, scheduling, throughput or model behavior.

The generic-description validator is tested; description generation is unsupported by the mock. Hosted review is not run. The structured ROUTE redesign remains a proposal. No training, linkage attack, threshold calibration, private-corpus rerun or real serving deployment is claimed.

## Templates

The banner source retains the supplied drawing code and changes only its wordmark text, tagline and diagram labels. The banner image in docs/assets/ was rendered from it. LICENSE and the root .gitignore are copied byte-for-byte from the supplied templates; their public credit remains intact.
