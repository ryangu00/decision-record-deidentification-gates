# The routing class held back

The final ROUTE class had 194 rows and failed the consistency gate at v6 and v7. The audit also kept finding new internal shorthand. Holding back the class reflects those two failures; it does not prove that all possible representations of routing tasks are undecidable.

## Attempted generic descriptions

`goaldesc.py` generated descriptions of project slugs from the slug plus up to 6 Task/Shape lines. Seeing only the slug had produced wrong interpretations, so task context was added. Requests asked for 3 to 10 generic words. Validation rejected empty/multiline descriptions, more than 12 words, years, lane-revealing words, private patterns and private tokens.

There were 41 slugs; 40 descriptions were accepted and one was rejected for a lane word. A placeholder-plus-description Goal was attached to 183 of 194 rows. ROUTE agreement stayed 0.680 before and after. The mock intentionally does not implement this generation request; the validator is tested offline.

## Field isolation

The ablation used the 185 ROUTE rows with Goal lines in both raw and v7 text. Against raw rows, compare:

- V1: raw text with only Goal replaced by its v7 placeholder and description.
- V2: raw text with only work-item codes mapped to distinct `ref_N` values.
- V3: v7 text with the raw Goal restored.

Each variant was run once, with 3 reads per side and seed 23, on 2026-09-22 from 20:06 to 20:18. Agreement/floor was 0.714/0.778 for V1, 0.773/0.773 for V2, and 0.784/0.768 for V3. V1 failed its threshold 0.728; V2 and V3 passed. The public `ablate.py` recreates the transformations on synthetic rows; it does not recreate those private results.

## Interpretation with its uncertainty intact

The pattern is consistent with project identity carrying a routing shortcut: replacing Goal alone fails while restoring Goal recovers agreement. It is not causal proof. Paired exact two-sided tests gave p = 0.085 for V3/V1, 0.144 for V2/V1 and 0.878 for V3/V2. None is significant at 0.05; V1 misses its threshold by only 1.4 points.

Raw-majority instability also matters. Across the three ablation runs, raw majorities matched in all runs for 140 of 185 rows (75.7 %). Between v6 and v7 they matched on 153 of 194 (78.9 %). The endpoint's cause of jitter was not isolated. [Results](results.md#routing-descriptions-and-ablation) supplies the full tables and derived conditions.

The held-back rows had mean state length 116 characters, range 32 to 204, with majority label share 56.7 %. They were 21.4 % of the 905 usable rows. The v7 mechanical scan still hit 4 rows and the ROUTE-only audit found 6 hard findings in 3 of 50. The shorthand list had not converged.

The label-accuracy diagnostic also prevents an overclaim: ROUTE raw accuracy was 0.392 versus scrubbed 0.381 in v6, and 0.376 versus 0.412 in v7. Both raw and scrubbed readers were below the majority-label baseline. What failed was consistency with a weak raw reader, not a direct measurement of training signal.

## Proposal that was not done

Re-extract from structured task attributes: a shape enum, risk level, estimate and whether production files are touched. The intended change is to make labels depend on task properties rather than project identity. Rerun the audit and all gates on that new representation.

This routing re-extraction was proposed but not performed. The estimate of half a day of local compute and two audit rounds was not measured. No source schema or measured outcome for that redesign is available, so the public code does not pretend to implement or validate it.

**Rule:** isolate the field that appears to carry the loss, preserve uncertainty, and hold back a class rather than lowering the acceptance line to keep it.
