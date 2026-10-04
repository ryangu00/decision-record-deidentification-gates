# Results: historical runs, derived diagnostics, and synthetic checks

These tables transcribe the supplied experiment record. The private row-level outputs, maps, reviewer tables and dataset are not published. They cannot be independently recomputed from this repository. All original runs were on 2026-09-22; retrospective calculations are dated 2026-10-04 in the supplied record. Those dates are retained as source dates, not claimed as dates of this repository's tests.

The new gate options did not produce the historical convergence numbers. PASS below means the original gate's majority agreement was at least its single-pair floor minus 0.05. It does not mean privacy, correctness or training quality was proven.

## Setting

Conditions: the shared local endpoint and hosted audit described below apply to the original runs; exact per-run engine build was not recorded.

| Item | Value |
|---|---|
| Runs | 2026-09-22; first scrub 17:47 local, last ablation 20:18 local |
| Derived diagnostics | Recomputed from saved per-row outputs on 2026-10-04, according to the supplied record |
| Hardware | Two Dell Pro Max with GB10 machines, tensor parallel |
| Model | Qwen3.8-Flash-Next (NVFP4), same served model for scrubber, reader, leak checker and description writer |
| Thinking | `chat_template_kwargs.enable_thinking=false` |
| Serving recipe | vLLM, community cluster recipe, fp8 KV cache, MTP4 speculative decoding, async scheduling off |
| Recipe build | `v0.1.dev20759+gb40673cd0` in the related cookbook; exact build for these runs not recorded |
| Requests | Temperature 0; scrub `max_tokens=900`; readout `max_tokens=2`, `logprobs=true`, `top_logprobs=20` |
| Retry policy | Timeout 180 s; 2 attempts; 2 s back-off |
| Reviewer | Hosted frontier model, read-only sandbox, maximum reasoning effort, instructions prohibiting network use and file writes; read a 50-row file |
| Tools | Python 3 standard library, including `difflib`; source scripts compile on 3.14.6 |
| Scale | 905 usable rows: ROUTE 194, REVIEW 679, ARCH 32; 711 delivered: REVIEW 679 and ARCH 32; ROUTE 194 held back |

## Extraction schema

Conditions: final extraction design; the original ARCH prompt lacked the leak guard, and REVIEW contexts were removed later.

| Class | State | Question | Options | Label | Leak controls |
|---|---|---|---|---|---|
| ROUTE | Task, Shape, Goal | Which execution lane should take this task? | Fixed 9-value lane vocabulary | Normalized actual lane | Declared lane, result and rework only in extra; bare task identifiers back-filled from the what cell only |
| REVIEW | Reviewer finding, initially with up to 3 context lines | Should the author apply this reviewer finding? | APPLY, REJECT | Verdict cell | Change column never copied; all file context later dropped |
| ARCH | Generated 2-4 sentence pre-decision situation from first 6,000 characters | Which option did the team choose? | 2 to 9 options; text-hash-seeded shuffle | Chosen option text | Decision-word ban; 25-character common-substring or 60 % token-overlap rejection; tokens at least 3 characters; one retry then drop |

## Extraction results

Conditions: 2026-09-22; private source records; audit observations are from the stated rounds and sample sizes.

| Measurement | Value | Conditions |
|---|---|---|
| Routing ledger rows extracted | 204 | One per ledger line; 195 at specification time |
| Review findings extracted | 679 | 689 table rows in specification; 499 resolved file context |
| Review verdict balance | APPLY 622, REJECT 57 (91.6 % APPLY) | Delivered rows |
| ARCH first prompt | 157 read, 157 kept | No leak guard |
| ARCH guarded prompt | 157 read, 131 kept, 26 dropped, 0 option leaks logged | Dropped as label_leak after retry |
| First ARCH audit | 8 of 17 stated the decision, 2 more paraphrased it (10 of 17) | Round 1, 50-row sample |
| Next ARCH audit | 1 explicit leak plus 1 uncertain in 17 ARCH rows | Round 2 |
| Bare task identifiers after back-fill | 13 | Project file had been archived |

## Mechanical gate

Conditions: 2026-09-22; stages have different populations and include carried failures; these are not one additive funnel.

| Stage | Rows | Passed | Failed | Notes |
|---|---|---|---|---|
| First scrub, ROUTE + REVIEW | 883 | 880 | 3 | Internal names: person, bot, lane abbreviation |
| First scrub, ARCH | 157 | 152 | 5 | 1 IP, 2 paths, 2 internal names; options and label also scrubbed |
| Second ARCH scrub | 131 | 128 | 3 | Guarded extraction; internal-name pattern |
| Case-insensitive post-pass, same ARCH set | 128 | 124 | 4 | Names hidden by case sensitivity |
| Post-pass at v3 | 1,014 | n/a | 10 including earlier failures | 169 rows changed |
| After all steps, v5 to v7 | 922 | 905 | 17 | 6 earlier failures, 7 label_in_state, 4 case-insensitive hits |
| Final rescan, v7 | 905 | REVIEW 679 and ARCH 32: zero hits | 4 ROUTE rows hit | Internal shorthand |

Conditions: private configuration versions, not the synthetic example files shipped here.

| Configuration | v1 | v2 |
|---|---|---|
| Token-table entries | 9 | 29 |
| Regex lines | 4 | 4 |

The public keep-list in the historical run had 28 entries. The internal-name alternation in v2 had 18 alternatives. The final rescan added 5 new words. None of those private lists is shipped.

## Shared-map repair

Conditions: 523 entries at the time of repair on 2026-09-22; classification uses the first matching reason.

| Classification | Count |
|---|---|
| Kept | 243 |
| Malformed placeholder | 88 |
| Original shorter than 4 characters | 40 |
| Original in public keep-list | 10 |
| Original a class word or placeholder-shaped string | 142 |
| Total dropped | 280 |

Conditions: recorded map-repair diagnostics and later post-pass versions; the poisoning mechanism is inferred, not experimentally isolated.

| Measurement | Value |
|---|---|
| Numbered-placeholder originals renumbered | 116 of 523; all 116 changed to a different placeholder |
| Placeholders shared by multiple originals | 17; most shared by 16 |
| Map repair | 523 -> 243 entries |
| Poisoned replacements reversed | 192 |
| Rows changed | 611 of 1,014 |
| Recorded kept-map class breakdown | project 214, month 35, bot 21, id 12, node 10, vendor 10, person 7, persona 5 |
| Distinct codes | 91 at v5; 93 at v6 and v7 |
| Severity tags replaced by an unknown project | 127 REVIEW rows at v5 |
| Tags restored by alignment | 126 in final run; source comment says 127 |
| v6 alignment outcomes | severity 126, plain word 4, project slug 17 |
| Rows still in unknown-project bucket | 12 |

Source discrepancy: the recorded class breakdown does not reconcile with the stated 243 kept entries. Both are retained rather than silently repaired; their snapshot relationship is unknown. Likewise, the restoration count is 126, not the comment's 127.

## Original decidability runs

Conditions: all 2026-09-22; majority of 3 reads per side versus raw read 1/read 2 agreement; slack 0.05; raw options on both sides.

| Run | Class | n | Agreement | Floor | Verdict |
|---|---|---|---|---|---|
| Earliest scrub, 80-row sample | ROUTE | 40 | 0.725 | 0.800 | FAIL |
| Earliest scrub, 80-row sample | REVIEW | 40 | 0.950 | 0.925 | PASS |
| ROUTE re-scrub with lane-name seed map | ROUTE | 40 | 0.750 | 0.725 | PASS |
| v1 full set, seed 11; slug clear in 175 of 192 Goal lines | ARCH | 40 | 1.000 | 1.000 | PASS |
| Same v1 run | ROUTE | 40 | 0.850 | 0.725 | PASS |
| Same v1 run | REVIEW | 40 | 0.975 | 0.975 | PASS |
| v5, code_N, seed 13 | ARCH | 32 | 1.000 | 1.000 | PASS |
| Same v5 run | ROUTE | 40 | 0.600 | 0.750 | FAIL |
| Same v5 run; raw REVIEW context still affects comparison | REVIEW | 40 | 0.900 | 1.000 | FAIL |
| v6, ref_N, raw REVIEW context stripped, seed 17 | ARCH | 32 | 1.000 | 1.000 | PASS |
| Same v6 run | ROUTE | 194 | 0.680 | 0.784 | FAIL; threshold 0.734 |
| Same v6 run | REVIEW | 200 | 0.950 | 0.970 | PASS; threshold 0.920 |
| v7, generic descriptions, ROUTE only, seed 19 | ROUTE | 194 | 0.680 | 0.763 | FAIL; threshold 0.713 |

The initial single-read policy was 0.95. The earliest comparable ROUTE check gave 10 of 18 agreements (0.556), motivating repeated reads and a floor. No ROUTE or REVIEW gate ran for versions 2, 3 and 4; only ARCH was checked for version 2, without a numerical result supplied here. The first red ROUTE result after replacing project identity arrived at v5, after four audit rounds.

## Repeated raw reads

Conditions: identical raw text, temperature 0; derived from saved original reads, recomputed 2026-10-04.

| Run | Class | n | All 3 raw reads agree | Share |
|---|---|---|---|---|
| v6 | ROUTE | 194 | 127 | 65.5 % |
| v6 | REVIEW | 200 | 188 | 94.0 % |
| v6 | ARCH | 32 | 32 | 100 % |
| v7 | ROUTE | 194 | 130 | 67.0 % |

Conditions: raw-majority agreement across separate runs of identical raw rows, not raw versus scrubbed agreement.

| Comparison | Rows with identical raw majorities | Share |
|---|---|---|
| All three ablation runs, n=185 | 140 | 75.7 % |
| v6 versus v7 ROUTE, n=194 | 153 | 78.9 % |

The endpoint was shared with live traffic and used speculative decoding. Neither was isolated as the cause of jitter.

## Retrospective diagnostics

Conditions: computed on 2026-10-04 from saved outputs; these were not part of the original pass/fail gate.

| Diagnostic | Result |
|---|---|
| ROUTE v6 floor estimators | Single pair 0.784; mean of 3 pairs 0.763 |
| ROUTE v7 floor estimators | Single pair 0.763; mean of 3 pairs 0.773 |
| Floor estimator movement | About 2 percentage points against 5-point slack |
| ROUTE gap to floor | 8 to 10 points: 0.680 versus 0.763 to 0.784 |
| v6 ROUTE agreement by raw stability | Unanimous: 0.780 on 127; split: 0.493 on 67 |
| v7 ROUTE agreement by raw stability | Unanimous: 0.800 on 130; split: 0.438 on 64 |
| v1 ROUTE, slug in clear | Unanimous: 0.926 on 27; split: 0.692 on 13 |
| Flips with unanimous raw reads | v6: 28 of 62; v7: 26 of 62 |
| REVIEW answer marginals | Raw majority APPLY on 189 of 200; scrubbed on 187 |
| REVIEW chance agreement | 0.887, versus threshold 0.920 and observed 0.950 |
| v6 ROUTE label accuracy | Raw 0.392, scrubbed 0.381; majority label share 0.567 |
| v6 REVIEW label accuracy | Raw 0.875, scrubbed 0.885; majority share 0.910 |
| v6 ARCH label accuracy | Raw 0.938, scrubbed 0.938; n=32 |
| v7 ROUTE label accuracy | Raw 0.376, scrubbed 0.412 |
| Delivered ARCH options changed | 7 of 32; original gate never read these changed options |
| Same v1 sample on later data | v6: 26 of 40 (0.650); v7: 29 of 40 (0.725) |
| Remaining v6 ROUTE rows | 106 of 154 (0.688) |
| Sampling standard error | About 0.07 at n=40; about 0.03 at n=194 |

The early pass cannot be explained by sampling alone: the project slug remained in clear in v1 and was replaced from v3 onward. Agreement is a consistency proxy; ROUTE reader label accuracy was below the majority baseline before and after scrubbing.

## Label-leak routes

Conditions: controls accumulated during the original runs; severity labels here use the synthetic public convention.

| Route | Mechanism | Control |
|---|---|---|
| ARCH restates decision | Generated situation quotes the chosen action | Guarded prompt, overlap filter, retry, drop |
| ARCH rejects alternative | Rejection reveals answer in a 2-option row | Semantic leak gate |
| ROUTE names lane | Task instruction names its own label | label_in_state rejection; 7 removed |
| REVIEW revised-file context | Current file already contains the accepted repair | Drop context on both comparison sides |
| REVIEW change column | Explicitly says what the author did | Never copied |

## Semantic leak filter

Conditions: 2026-09-22, 124 usable ARCH rows after guarded extraction and mechanical failures; 3 reads, median p(yes), threshold 0.5, uncalibrated.

| Measurement | Value |
|---|---|
| Entering ARCH rows | 124 |
| Dropped | 92 (74 %) |
| Delivered | 32 |
| Dropped p(yes) | 0.5 to 0.6: 11; 0.6 to 0.8: 38; 0.8 to 1.0: 43 |
| Kept p(yes) | Below 0.2: 11; 0.2 to 0.4: 14; 0.4 to 0.469: 7; maximum 0.469 |
| Dropped rows straddling threshold across reads | 9 of 92 |
| Verbatim state-contains-label in next audit | 0 of 50 in round 3; 1 suspected ROUTE row in round 4, then 7 same-pattern rows dropped |
| End-to-end ARCH yield | 32 out of 157 (20 %) |
| REVIEW raw contexts | 499 of 679; all dropped |
| Delivered REVIEW labels | APPLY 622, REJECT 57 |

## Independent audit record

Conditions: hosted reviewer, 2026-09-22, different data versions and samples; 50 rows per round; no repeated-sample variance measurement. Final-rule re-tally is a single-reader retrospective judgment, with uncertain items retained as uncertain.

| Round | Data | Sample | Reviewer count | Final-rule re-tally | Findings | Next change |
|---|---|---|---|---|---|---|
| 1 | v1 | Up to 17 per class | LEAKS (52) | 34 hard, 18 allowed | 11 label leaks; 15 internal names/slugs/scripts/components; 6 day residues; 2 placeholder defects | Case-insensitive all-field gate, Goal replacement, token table, guarded ARCH extraction |
| 2 | v2 | Up to 17 per class | LEAKS (28) | 17 hard, 2 uncertain, 9 allowed | 13 identifiers; 1 day residue; 2 placeholder defects; 1 elimination leak | Map cleanup, larger table, semantic leak gate |
| 3 | v3 | Recorded as 17 per class; total 50 | LEAKS (27) | 7 hard, 2 uncertain, 18 allowed | 5 codes, 1 alias, 1 malformed placeholder; 0 of 50 verbatim leaks; REVIEW 16 of 16 APPLY; context suspected | Code/alias/placeholder repairs; context drop |
| 4 | v4 | 17 ROUTE, 8 APPLY + 8 REJECT, 17 ARCH | LEAKS (28) | 4 hard + 5 self-inflicted collisions + 19 allowed | Lane named, trailing letter, internal identifier, slug; distinct-code collapse | Distinct code_N, label-in-state rule |
| 5 | v5 | Balanced as round 4 | LEAKS (1) | 1 hard | Scheduled-job name | ref_N, unknown-project alignment, raw context stripping, full ROUTE gate |
| 6 | v6 | Balanced, new seed | CLEAN | 0 hard | Notes only: unclear system name, experiment code, task range | Extend token/code tables |
| 7 | v7 | 50 ROUTE | LEAKS (6) | 6 hard in 3 rows | Task code, alias, configuration code, three experiment codes | Hold ROUTE back |

The record describes round 3 as “17 per class” while also reporting 50 total and 16 REVIEW; retain the total and observed REVIEW count rather than treating that shorthand as exact arithmetic. Early samples used seeds 23, 29, 31 and were shuffled before truncation. Later samples were verdict-stratified.

Conditions: two different counting rules; round 7 is ROUTE-only and cannot be treated as the next mixed-class sample.

| Ruler | Round 1 | Round 2 | Round 3 | Round 4 | Round 5 | Round 6 | Round 7 |
|---|---|---|---|---|---|---|---|
| Reviewer | 52 | 28 | 27 | 28 | 1 | 0 | 6 |
| Final-rule re-tally | 34 | 17 | 7 | 9 | 1 | 0 | 6 |

The old note “24 of 28 allowed” for round 4 is superseded by 19 allowed, 5 self-inflicted and 4 hard. The rule was written after round 3, before round 4, but was not inserted into the prompt until round 5.

Conditions: statistical interpretation assumes random row sampling; the actual mixed sample was stratified and does not certify any individual class.

| Audit diagnostic | Value |
|---|---|
| Zero findings in 50 random rows | About 5.8 % row-level upper bound at 95 % confidence: 1 - 0.05^(1/50) |
| ROUTE rows in round 6 | 17 |
| Round 7 affected ROUTE rows | 3 of 50 (6 %) |
| Hosted row-views | 350 across 7 calls; not a count of unique records |

Samples were sent to a hosted model. Early samples contained private identifiers. The egress pre-check covered prompts but not samples. The instruction “no network” inside a reviewer prompt did not prevent model-service egress.

## Routing descriptions and ablation

Conditions: descriptions at v7 on 2026-09-22; local model saw a slug and up to 6 Task/Shape lines; request 3 to 10 words, validation at most 12 words, no year/lane/pattern/token hits.

| Description step | Value |
|---|---|
| Project slugs | 41 |
| Accepted descriptions | 40 of 41; one rejected for a lane word |
| Rows with descriptions | 183 of 194 |
| ROUTE agreement before / after | 0.680 / 0.680 |

Conditions: 185 matched ROUTE rows with a Goal line on both sides; 3 reads per side, seed 23, one run per variant; 2026-09-22 20:06 to 20:18, about 4 minutes each.

| Variant | Only change | Agreement | Floor | Verdict |
|---|---|---|---|---|
| V1 | Raw text, Goal replaced by v7 placeholder plus description | 0.714 | 0.778 | FAIL; threshold 0.728 |
| V2 | Raw text, work-item codes replaced by ref_N | 0.773 | 0.773 | PASS, no loss |
| V3 | v7 text, raw Goal restored | 0.784 | 0.768 | PASS, no loss |

Conditions: retrospective paired exact two-sided tests on agreeing rows, derived 2026-10-04; no pair reaches 0.05 significance.

| Statistical check | Result |
|---|---|
| V3 versus V1 | 31 versus 18 discordant rows; p = 0.085 |
| V2 versus V1 | 29 versus 18; p = 0.144 |
| V3 versus V2 | 22 versus 20; p = 0.878 |
| V1 shortfall against threshold | 1.4 points |

Conditions: final private ROUTE population; identity-shortcut interpretation remains suggestive, not proven.

| Routing facts | Value |
|---|---|
| Held back | 194 |
| Label distribution | self 110, other 33, second agent 32, sub-agent 10, local model 4, cheap-cloud batch 2, workflow 2, cheap-cloud review loop 1; majority 56.7 % |
| Share of usable rows | 21.4 % of 905 |
| State length | Mean 116 characters; range 32 to 204 |
| v7 mechanical rescan | 4 rows hit |
| Round 7 audit | 6 hard findings in 3 of 50 |
| v6 and v7 flips | 62 of 194 in each; about 20 distinct raw-to-scrubbed letter pairs |

## Held back or dropped

Conditions: different pipeline stages, not mutually exclusive counts to sum; all private intermediate artifacts remain unpublished.

| Item | Count | Reason |
|---|---|---|
| Final ROUTE | 194 | Two decidability failures and non-converging shorthand |
| Earlier ROUTE removals | 3 mechanical, 7 label_in_state | Fail-closed rules |
| ARCH extraction drops | 26 of 157 | Decision still exposed after retry |
| ARCH semantic drops | 92 of 124 | Median p(yes) >= 0.5 |
| ARCH mechanical drops | 3 plus 4 of 131 | Summary lists names, IPs and paths; stage table identifies these guarded-set failures as internal-name hits |
| REVIEW context | 499 contexts, all dropped | Revised-file leak |
| REVIEW delivered | 679 of 679 extracted | 91.6 % APPLY |
| Prior versions v1 to v6, maps, token/pattern files, samples | All private | Not shipped |

## Timeline and cost

Conditions: local wall-clock times on 2026-09-22; durations are reported values, not recomputed from rounded clock labels.

| Local time | Step | Duration |
|---|---|---|
| 17:38 to 17:41 | First gate, 80-row sample | 2.6 min |
| 17:47 to 18:24 | Scrub 883 ROUTE and REVIEW | 37.5 min |
| 18:24 to 18:37 | Scrub 157 ARCH, options and labels included | 12.6 min |
| 18:37 to 18:41 | Gate, 40 per class | 3.2 min |
| 18:41 to 18:45 | Audit round 1 | 4.3 min |
| 18:50 to 19:17 | ARCH re-extraction 15.9 min, scrub 10.3 min, post-pass | 26 min |
| 19:23 to 19:25 | Map repair, post-pass, leak gate | 2 min |
| 19:36 to 19:41 | v5 post-pass, gate about 2 min 50 s, audit | 4.8 min |
| 19:45 to 19:55 | v6 post-pass, expanded gate, audit | 10.6 min |
| 19:58 to 20:04 | v7 descriptions, ROUTE gate, audit | 6.3 min |
| 20:06 to 20:18 | Three ablation variants | 11.8 min |

First scrub to last ablation: 2 h 31 min. Logged reviewer calls took 1.7 to 4.3 minutes. Local readouts were about 0.21 s each: 1,164 reads for 194 rows x 2 sides x 3 reads in about 4 min 8 s. Local inference had no per-token charge; hosted review was the paid/external component, with 7 calls. No monetary total is supplied. Seven data versions in about 2.5 hours required repeated human adjudication.

## Historical synthetic mock checks

Conditions: source records these checks on 2026-10-04 against the original scripts; synthetic fixtures, not the private corpus. Public adapters use generic class names and rename the success marker.

| Step | Command shape | Recorded output |
|---|---|---|
| Extract | extract.py with routing, reviews, adr, goals and mock /v1 base | ROUTE read 36 kept 36, enriched 6; REVIEW kept 40; ARCH read 8 kept 8; total 84 |
| Scrub | scrub.py with map and fixture patterns | 84 rows; 84 passed; 0 failed; 0 model failures; map entities 6 |
| Map clean | mapclean.py with 2-line keep-list | Kept 6, dropped 0, reversed 0, rows changed 0 |
| Deterministic repair | postscrub2.py with raw, map and codes | 84 rows, 76 changed, 12 codes, 0 failed |
| Leak filter | leakcheck.py | Kept 84; 76 pass-through; dropped 0 |
| Decidability | decid3.py --per-gate 30 --reps 3 | ARCH 1.000/1.000, ROUTE 1.000/1.000, REVIEW 1.000/1.000; PASS |

Conditions: synthetic planted bias and stochastic mock; these are recorded demonstration results, not quality measurements of a real model.

| Mock check | Recorded result |
|---|---|
| code_N bias, neutral ref_N input | ROUTE agreement 1.000, PASS |
| code_N bias, codes renamed code_N | ROUTE agreement 0.667, floor 1.000, FAIL |
| Per-read flip probability 0.25 | Floors 0.57 to 0.73; across three seeds at n=30 the same REVIEW data alternated PASS/FAIL |

The original fixture had 36 ROUTE rows, 40 REVIEW rows, 8 architecture records, a task table, a 7-pattern file and a 2-entry keep-list. The public example pattern file adds the generic credential/home-path checks; its configuration is not the historical private pattern file. Current test output belongs in the test run, not in these historical tables.
