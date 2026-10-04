# Pitfalls: symptoms, causes and bounded fixes

These failure modes come from the supplied experiment record. A fix can remove one failure while introducing another; every changed stage invalidates downstream evidence. New public-adapter behavior is listed separately in [implementation notes](implementation.md).

## Extraction and invocation

| Symptom | Root cause | Fix and limit |
|---|---|---|
| Requests return 404 | Caller passes a base without /v1, but scripts append /chat/completions | Use a /v1 base consistently. The mock rejects other endpoint paths |
| Foreground extraction stops unexpectedly | First long ARCH run hit a 580 s tool limit | Use a detached local job with a log; a partial file is not a completed extraction |
| Task state is only a bare identifier | Ledger stored an identifier instead of a description | Back-fill only the task table's what cell; mark unavailable enrichment rather than reading route/status |
| ARCH context directly reveals a decision | Context-generation prompt had no choice ban | Add the prompt guard, overlap check and retry/drop policy, then apply the separate semantic filter |
| ARCH wording is mistaken for a quotation | Extraction translated mixed-language source while summarizing | Label it generated paraphrase; no verbatim-source fidelity is established |
| An execution lane consumes time without producing usable work | Its hooks conflicted with shell/network helpers | Keep the format specification free of private names and run the data-processing scripts locally; do not present the failed attempt as a pipeline result |

The guarded extractor still sees the decision record. A textual instruction to ignore the label cannot guarantee label-blind construction. Its thresholds were uncalibrated, and downstream filtering found many remaining leaks.

## Mechanical checks

| Symptom | Root cause | Fix and limit |
|---|---|---|
| Capitalized private name survives | Case-sensitive gate | Case-insensitive matching from the first check |
| State passes while options contain names | Scan covered state only | Scan state, options and label; scan the entire final payload before egress |
| Public products become opaque placeholders | Scrubber over-replaces | Keep a public keep-list and remove those mappings during validation |
| A month placeholder retains a day | Model masks only part of the date | Strip the adjacent day deterministically and rerun the gate |
| Goal replacement misses a month placeholder | Lowercase-only slug regex | Match the complete value rather than a narrow slug spelling |
| Goal replacement misses rewritten words | Regex assumes no spaces | Configurable prefix/value capture over the whole line |
| More private shorthand appears every round | Mechanical enumeration cannot cover unknown names | Extend the list, but hold back the non-converging class rather than treating list growth as proof of safety |

Patterns are code: malformed or empty lists must not quietly become a permissive configuration. The public adapter rejects them, reports a failure without echoing private content, and tests those paths.

## Maps and repairs

| Symptom | Root cause | Fix and limit |
|---|---|---|
| Placeholders change number across rows | Model returns existing placeholders as new entities | Validate map originals and reject placeholder-shaped ones during cleanup |
| Generic words become glued fragments | Plain substring replacement inside longer words | Avoid boundary-free replacement in a production redesign; the adapter retains and documents the historical risk |
| One placeholder appears to mean multiple things | Unknown bucket plus poisoned renumbering | Preserve an explicit unknown, inspect same-record collisions and reject collapsed options |
| Distinct targets have identical option text | All codes collapsed to one literal | Give each distinct code its own neutral ref_N and enforce option uniqueness |
| Placeholder ends with stray letters or repeated suffixes | Model appends text to placeholder forms | Normalize nested, doubled, plural and trailing-letter forms, then check again |
| Severity becomes an unknown project | Scrubber treats a review tag as an entity | Align raw and scrubbed tokens, restoring only recognized configured severity tags |
| Routing reader drifts toward one lane | Placeholder name code_N carries meaning | Use the measured neutral ref_N replacement; rerun the gate instead of assuming neutrality |

The reported map class breakdown does not reconcile with the reported retained-map total. The private snapshots are unavailable here, so the inconsistency is retained explicitly in the results rather than patched with a guessed explanation.

## Decidability and labels

| Symptom | Root cause | Fix and limit |
|---|---|---|
| Single-read agreement looks poor at temperature 0 | Reader disagrees with itself | Measure a raw self-agreement floor and repeated majorities; cause of the endpoint jitter remains unknown |
| Early small sample passes, later full set fails | Data representation changed as well as sample | Compare the same rows across versions; do not blame sampling alone |
| REVIEW fails after context removal | Raw side still shows revised-file context | Strip the same field from both comparison sides |
| Gate passes although delivered options differ | Original gate reuses raw options | Enable the new scrubbed-options path and preserve option order |
| Flips are attributed to no placeholder class | Original regex omitted ref_N and id_N | Include those classes; presence is still association, not causal proof |
| REVIEW agreement looks strong | APPLY-heavy marginals produce high chance agreement | Report both marginals and their chance agreement next to the observed rate |
| Perfect ARCH floor seems too reassuring | Stable reads can still share model blind spots or unchanged raw options | Check delivered options and retain independent audit and label-leak checks |
| ARCH yield collapses | Extraction and semantic filters remove different leak routes | Report each stage's denominator, retained rows and dropped rows |
| REVIEW audit sample contains only APPLY | Highly imbalanced corpus and random sampling | Stratify by label, while reporting the actual resulting composition |

An unstable raw reader is a weak reference. ROUTE label accuracy was below the majority-label share before and after scrubbing; consistency failures cannot by themselves establish that useful training signal was destroyed.

## Audit and routing

| Symptom | Root cause | Fix and limit |
|---|---|---|
| Reviewer repeatedly lists allowed public paths | Acceptance rule absent from prompt | Put the exact rule into the prompt and count hard findings only |
| Counts appear to converge suddenly | Counting rule, data and sample all changed | Publish both rulers and the sample composition of every round |
| CLEAN is followed by ROUTE leaks | Mixed sample gives limited class coverage | Audit each class separately; do not infer class clearance from the mixed sample |
| Prompt passes but private data reaches a hosted reviewer | Pre-check scans only the prompt | Scan the sample too; read-only/no-network task instructions do not prevent hosted-model egress |
| Generic project description invents the wrong domain | Generator saw only a slug | Provide task lines and validate output; this still gave no measured agreement gain |
| A failure is blamed on the whole scrub | One field may carry the identity shortcut | Isolate Goal and code transformations in separate ablations |
| Project-identity explanation is stated as proven | One run per variant and non-significant paired tests | Call it suggestive, retain the raw-stability caveat and the full-set failures |
| Held-back data vanishes from reporting | Only delivered totals shown | Report 194 ROUTE rows held back and why |

The proposed fix for ROUTE is structured re-extraction from task attributes. It was not done. The private-data experiment does not supply a ready schema, trained result or calibrated estimate for that redesign.

**Operating rule:** each repair is a new transformation. Recheck its privacy, distinctions, label independence, consistency and outbound sample before accepting its output.
