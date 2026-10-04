# Decidability: consistency against an unstable reader

The gate asks whether a fixed reader makes the same choice before and after scrubbing. It does not ask whether either answer is correct. It does not read the recorded labels when making its pass/fail decision.

## Readout contract

Build a prompt from state, a blank line, question, lettered options and a final “None of these; escalate” option. The system requests exactly one capital letter. Request temperature 0, thinking disabled, max_tokens 2, logprobs true and top_logprobs 20. Read only the first generated token's alternatives.

Trim token whitespace, take its first character and retain valid option letters. Missing letters receive minimum observed logprob minus 3. Softmax those scores and choose the largest. This reproduces the historical first-character parser; it is not a general answer parser. Each call has the recorded timeout/retry policy.

Sample by class with a seeded shuffle. For each row, read raw and scrubbed sides 3 times and choose the majority letter. The historical tie handling selects the first observed among equally frequent answers. The original floor compares only raw reads 1 and 2, even though the measured cross-side agreement compares majorities.

For a class of n rows, agreement is the number of equal majorities divided by n. The historical floor is the number of matching first raw pairs divided by n. Pass if agreement >= floor - 0.05. The 0.05 slack and early 40-row sample size were policy choices, not calibrated values.

## Why repeated reads matter

On the earliest 18 comparable ROUTE rows, a single-read check gave 0.556 and made the initial 0.95 target unusable. At v6, only 127 of 194 raw ROUTE rows had all 3 reads agree. At v7, it was 130 of 194. Across the ablation runs, the same raw majority was retained on 140 of 185 rows. Endpoint noise is not a minor theoretical caveat here.

The original endpoint shared live traffic and used speculative decoding; neither cause was isolated. Do not attribute the jitter to either from these runs. The [complete tables](results.md#original-decidability-runs) retain every recorded gate run and the [derived diagnostics](results.md#retrospective-diagnostics) separate later calculations.

The v1 ROUTE pass was also a data-version effect. Project identity remained clear in 175 of 192 Goal lines. The same sampled rows scored 0.650 on v6 and 0.725 on v7; the other 154 scored 0.688 on v6. Calling the original pass only a sampling accident discards that evidence.

## Improvements implemented after the original runs

These options are new public code, exercised against synthetic clean/noisy/biased mock responses. They have not been run against the private corpus and must not be credited with the published convergence results.

| Option | Behavior | Testable distinction |
|---|---|---|
| `--scrubbed-options` | Read delivered options on the scrubbed side | An option-only code_N bias is invisible on the historical option path and detected with this flag |
| `--stability-report` | Separate unanimous raw reads from split raw reads | Report each stratum's n and agreement; an empty stratum has no agreement estimate |
| `--floor-estimator mean-pairs` | Mean the three raw-pair agreements | Requires exactly 3 reads; a split row can have a perfect first pair but a lower mean |

The default standalone gate retains the original raw-options/single-pair choices for comparison. The runner explicitly enables all the improvements. Positional option correspondence must remain intact: the gate rejects differing option counts and duplicate delivered options, but cannot prove that an arbitrary reordered free-text list preserves meaning.

Attribution now includes `ref_N` and `id_N`. It reports concrete placeholders present in flipped states; those associations are diagnostic, not causal attribution. It does not attribute an option-only change to a state placeholder that is absent.

Both floor estimators compare single reads; averaging pairs does not produce a majority-to-majority noise baseline. Stability stratification reports the unresolved difference rather than correcting it automatically. Marginals and their chance agreement are printed alongside every class result: sum the products of raw and scrubbed majority-letter proportions.

## Failure semantics and weak gates

The adapter rejects empty comparisons, missing raw counterparts, duplicate identifiers, incomplete reads and incompatible options. An API failure cannot lower the floor into a pass. The output contains per-row letters and summary diagnostics, not raw content.

REVIEW is strongly imbalanced. Its original raw and scrubbed majority marginals implied chance agreement 0.887, close to threshold 0.920 and observation 0.950. ARCH appeared stable, but the original gate reused raw options on both sides even for 7 of 32 rows with changed options. ROUTE label accuracy was below the majority baseline before and after scrubbing. Passing consistency therefore does not establish useful labels or useful training signal.

**Rule:** keep self-agreement, chance agreement, label accuracy and training quality conceptually separate. Only the first two are outputs of this gate.
